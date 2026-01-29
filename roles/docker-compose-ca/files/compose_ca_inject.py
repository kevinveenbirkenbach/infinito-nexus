#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


def die(msg: str, code: int = 2) -> "None":
    print(f"[compose_ca_inject] {msg}", file=sys.stderr)
    raise SystemExit(code)


def run(cmd: List[str], *, cwd: Path, env: Dict[str, str]) -> Tuple[int, str, str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def run_checked(cmd: List[str], *, cwd: Path, env: Dict[str, str], label: str) -> None:
    rc, out, err = run(cmd, cwd=cwd, env=env)
    if rc != 0:
        details = (err or out).strip()
        die(f"{label} failed (rc={rc}): {details}")


def parse_yaml(text: str, label: str) -> Dict[str, Any]:
    try:
        doc = yaml.safe_load(text)
    except Exception as e:
        die(f"Failed to parse YAML for {label}: {e}")
    if not isinstance(doc, dict):
        die(f"{label} must be a mapping at top-level")
    return doc


def normalize_cmd(value: Any) -> List[str]:
    """
    Normalize a docker-compose 'command' value into exec-form list[str].

    Supported:
      - list[str] => as-is
      - string    => shell-form: ["/bin/sh", "-lc", "<string>"]
      - None      => []
    """
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        return value
    if isinstance(value, str) and value.strip():
        return ["/bin/sh", "-lc", value]
    die(f"Unsupported command type in compose config: {type(value)}")


def normalize_entrypoint(value: Any) -> List[str]:
    """
    Normalize a docker-compose 'entrypoint' value into exec-form list[str].

    Supported:
      - list[str] => as-is
      - string    => shell-form: ["/bin/sh", "-lc", "<string>"]
      - None      => []
    """
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        return value
    if isinstance(value, str) and value.strip():
        return ["/bin/sh", "-lc", value]
    die(f"Unsupported entrypoint type in compose config: {type(value)}")


def docker_image_inspect(
    image: str, *, cwd: Path, env: Dict[str, str]
) -> Tuple[List[str], List[str]]:
    """
    Return (Entrypoint, Cmd) for the given image in exec-form list[str].
    """
    rc, out, err = run(["docker", "image", "inspect", image], cwd=cwd, env=env)
    if rc != 0:
        die(f"docker image inspect failed for '{image}' (rc={rc}): {err.strip()}")

    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        die(f"docker image inspect returned invalid JSON for '{image}': {e}")

    if not isinstance(data, list) or not data:
        die(f"docker image inspect returned empty result for '{image}'")

    cfg = data[0].get("Config")
    if not isinstance(cfg, dict):
        die(f"docker image inspect missing Config for '{image}'")

    ep = cfg.get("Entrypoint")
    cmd = cfg.get("Cmd")

    if ep is None:
        ep_list: List[str] = []
    elif isinstance(ep, list) and all(isinstance(x, str) for x in ep):
        ep_list = ep
    else:
        die(f"Unexpected Entrypoint type for image '{image}': {type(ep)}")

    if cmd is None:
        cmd_list: List[str] = []
    elif isinstance(cmd, list) and all(isinstance(x, str) for x in cmd):
        cmd_list = cmd
    else:
        die(f"Unexpected Cmd type for image '{image}': {type(cmd)}")

    return ep_list, cmd_list


def docker_image_exists(image: str, *, cwd: Path, env: Dict[str, str]) -> bool:
    rc, _out, _err = run(["docker", "image", "inspect", image], cwd=cwd, env=env)
    return rc == 0


def ensure_image_available(
    *,
    service_name: str,
    svc: Dict[str, Any],
    image: str,
    compose_base_cmd: List[str],
    cwd: Path,
    env: Dict[str, str],
) -> None:
    """
    Ensure the referenced image exists locally.

    Strategy:
      1) If docker image inspect works -> OK
      2) Else:
         - If service has 'build' -> run `docker compose ... build <service>`
         - Otherwise -> run `docker compose ... pull <service>`
    """
    if docker_image_exists(image, cwd=cwd, env=env):
        return

    has_build = isinstance(svc.get("build"), (dict, str))
    if has_build:
        run_checked(
            compose_base_cmd + ["build", service_name],
            cwd=cwd,
            env=env,
            label=f"docker compose build {service_name}",
        )
    else:
        run_checked(
            compose_base_cmd + ["pull", service_name],
            cwd=cwd,
            env=env,
            label=f"docker compose pull {service_name}",
        )

    if not docker_image_exists(image, cwd=cwd, env=env):
        die(
            f"Image '{image}' for service '{service_name}' is still missing after build/pull."
        )


def _extract_compose_files(parts: List[str], *, cwd: Path) -> List[Path]:
    """
    Extract compose file paths from args like: ['-f','a.yml','-f','b.yml'].
    Resolve relative paths against cwd.
    """
    files: List[Path] = []
    i = 0
    while i < len(parts):
        if parts[i] == "-f":
            if i + 1 >= len(parts):
                die("Invalid --compose-files: '-f' without a filename")
            p = Path(parts[i + 1])
            if not p.is_absolute():
                p = cwd / p
            files.append(p)
            i += 2
            continue
        i += 1
    if not files:
        die("No compose files found in --compose-files (expected -f <file> ...)")
    return files


def _discover_profiles_from_files(compose_files: List[Path]) -> List[str]:
    """
    Discover all profile names referenced by any service across the compose files.
    """
    profiles: set[str] = set()
    for f in compose_files:
        if not f.exists():
            die(f"Compose file does not exist: {f}")
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except Exception as e:
            die(f"Failed to parse compose file '{f}': {e}")

        if not isinstance(doc, dict):
            continue
        services = doc.get("services")
        if not isinstance(services, dict):
            continue

        for _svc_name, svc in services.items():
            if not isinstance(svc, dict):
                continue
            p = svc.get("profiles")
            if isinstance(p, str) and p.strip():
                profiles.add(p.strip())
            elif isinstance(p, list):
                for x in p:
                    if isinstance(x, str) and x.strip():
                        profiles.add(x.strip())

    return sorted(profiles)


def _compose_base_cmd(*, project: str, parts: List[str], env_file: str) -> List[str]:
    cmd: List[str] = ["docker", "compose", "-p", project] + parts
    if env_file.strip():
        cmd += ["--env-file", env_file.strip()]
    return cmd


def _compose_cmd_with_profile(base_cmd: List[str], profile: str) -> List[str]:
    """
    Add a --profile <name> (global compose flag) to an existing base cmd.
    Expected base cmd: ['docker','compose', ...]
    """
    if len(base_cmd) < 2 or base_cmd[0] != "docker" or base_cmd[1] != "compose":
        die(f"Invalid compose base cmd: {base_cmd}")

    # Insert after 'docker compose'
    return base_cmd[:2] + ["--profile", profile] + base_cmd[2:]


def _load_services_via_config(
    *,
    compose_cmd: List[str],
    cwd: Path,
    env: Dict[str, str],
    label: str,
) -> Dict[str, Any]:
    rc, out, err = run(compose_cmd + ["config"], cwd=cwd, env=env)
    if rc != 0:
        die(f"docker compose config failed for {label} (rc={rc}): {err.strip()}")

    doc = parse_yaml(out, f"docker compose config output ({label})")
    services = doc.get("services")
    if not isinstance(services, dict) or not services:
        return {}
    return services


def render_override(
    services: Dict[str, Any],
    service_to_compose_cmd: Dict[str, List[str]],
    *,
    cwd: Path,
    env: Dict[str, str],
    ca_host: str,
    wrapper_host: str,
) -> Dict[str, Any]:
    """
    Generate a docker-compose override that injects CA trust into every service by:
      - mounting CA cert + wrapper script
      - setting entrypoint to the wrapper
      - setting command to the ORIGINAL effective command (final entrypoint + final command)
    """
    ca_container = "/tmp/infinito/ca/root-ca.crt"
    wrapper_container = "/tmp/infinito/bin/with-ca-trust.sh"

    out_services: Dict[str, Any] = {}

    for name, svc in services.items():
        if not isinstance(svc, dict):
            die(f"Service '{name}' must be a mapping in compose config")

        svc_ep = normalize_entrypoint(svc.get("entrypoint"))
        svc_cmd = normalize_cmd(svc.get("command"))

        image = svc.get("image")
        if not isinstance(image, str) or not image.strip():
            # If there is no image, we can only wrap if effective command is explicitly defined
            if not svc_ep and not svc_cmd:
                die(
                    f"Service '{name}' has no image and no entrypoint/command in composed config"
                )
            img_ep, img_cmd = [], []
            img_name = ""
        else:
            img_name = image.strip()
            compose_cmd = service_to_compose_cmd.get(name)
            if not compose_cmd:
                die(f"Internal error: missing compose cmd mapping for service '{name}'")

            ensure_image_available(
                service_name=name,
                svc=svc,
                image=img_name,
                compose_base_cmd=compose_cmd,
                cwd=cwd,
                env=env,
            )
            img_ep, img_cmd = docker_image_inspect(img_name, cwd=cwd, env=env)

        final_ep = svc_ep if svc_ep else img_ep
        final_cmd = svc_cmd if svc_cmd else img_cmd
        effective_cmd = final_ep + final_cmd

        if not effective_cmd:
            die(
                f"Service '{name}' resolved to empty effective command (image='{img_name or image}')"
            )

        out_services[name] = {
            "volumes": [
                f"{ca_host}:{ca_container}:ro",
                f"{wrapper_host}:{wrapper_container}:ro",
            ],
            "environment": {"CA_TRUST_CERT": ca_container},
            "entrypoint": [wrapper_container],
            "command": effective_cmd,
        }

    return {"services": out_services}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate docker-compose CA trust override via docker compose config"
    )
    ap.add_argument("--chdir", required=True, help="Compose instance directory")
    ap.add_argument("--project", required=True, help="Compose project name (-p)")
    ap.add_argument(
        "--compose-files",
        required=True,
        help='Compose files args string like: "-f a.yml -f b.yml"',
    )
    ap.add_argument("--env-file", default="", help="Optional env file path")
    ap.add_argument(
        "--out", required=True, help="Output filename (relative to --chdir or absolute)"
    )
    ap.add_argument(
        "--ca-host", required=True, help="Host path to CA cert (bind-mounted)"
    )
    ap.add_argument(
        "--wrapper-host",
        required=True,
        help="Host path to wrapper script (bind-mounted)",
    )
    args = ap.parse_args()

    cwd = Path(args.chdir)
    if not cwd.exists() or not cwd.is_dir():
        die(f"--chdir must be an existing directory: {cwd}")

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = cwd / out_path

    ca_host = str(args.ca_host).strip()
    wrapper_host = str(args.wrapper_host).strip()
    if not ca_host:
        die("--ca-host must be non-empty")
    if not wrapper_host:
        die("--wrapper-host must be non-empty")

    env = dict(os.environ)

    env_file = str(args.env_file).strip()
    if env_file:
        ef = Path(env_file)
        if not ef.is_absolute():
            ef = cwd / ef
        if not ef.exists():
            die(f"--env-file was provided but file does not exist: {ef}")

    parts = str(args.compose_files).strip().split()
    if not parts:
        die("--compose-files must be non-empty")

    # Base compose cmd (no profile)
    compose_base_cmd = _compose_base_cmd(
        project=str(args.project),
        parts=parts,
        env_file=str(args.env_file) if env_file else "",
    )

    # Discover all profiles referenced in compose files so we can include profile-only services too.
    compose_files = _extract_compose_files(parts, cwd=cwd)
    profiles = _discover_profiles_from_files(compose_files)

    # Load services from default config, then from each profile config, and merge.
    merged_services: Dict[str, Any] = {}
    service_to_compose_cmd: Dict[str, List[str]] = {}

    # 1) default (no profile)
    default_services = _load_services_via_config(
        compose_cmd=compose_base_cmd,
        cwd=cwd,
        env=env,
        label="default",
    )
    for svc_name, svc_def in default_services.items():
        merged_services[svc_name] = svc_def
        service_to_compose_cmd[svc_name] = compose_base_cmd

    # 2) each profile (adds profile-only services like "bootstrap")
    for p in profiles:
        cmd_p = _compose_cmd_with_profile(compose_base_cmd, p)
        prof_services = _load_services_via_config(
            compose_cmd=cmd_p,
            cwd=cwd,
            env=env,
            label=f"profile:{p}",
        )
        for svc_name, svc_def in prof_services.items():
            if svc_name not in merged_services:
                merged_services[svc_name] = svc_def
                service_to_compose_cmd[svc_name] = cmd_p

    if not merged_services:
        die("No services found after merging default + profile configs")

    override_doc = render_override(
        merged_services,
        service_to_compose_cmd,
        cwd=cwd,
        env=env,
        ca_host=ca_host,
        wrapper_host=wrapper_host,
    )

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        text = yaml.safe_dump(override_doc, sort_keys=True, default_flow_style=False)
        out_path.write_text(text, encoding="utf-8")
    except Exception as e:
        die(f"Failed to write output file {out_path}: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
