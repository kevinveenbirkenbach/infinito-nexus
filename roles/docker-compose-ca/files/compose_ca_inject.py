#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def parse_yaml(text: str, label: str) -> Dict[str, Any]:
    try:
        doc = yaml.safe_load(text)
    except Exception as e:
        die(f"Failed to parse YAML for {label}: {e}")
    if not isinstance(doc, dict):
        die(f"{label} must be a mapping at top-level")
    return doc


def normalize_cmd(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        return value
    if isinstance(value, str) and value.strip():
        return ["/bin/sh", "-lc", value]
    die(f"Unsupported command type in compose config: {type(value)}")


def docker_image_inspect(
    image: str, *, cwd: Path, env: Dict[str, str]
) -> Tuple[List[str], List[str]]:
    rc, out, err = run(["docker", "image", "inspect", image], cwd=cwd, env=env)
    if rc != 0:
        die(f"docker image inspect failed for '{image}' (rc={rc}): {err.strip()}")

    import json

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


def render_override(
    services: Dict[str, Any],
    *,
    cwd: Path,
    env: Dict[str, str],
    ca_host: str,
    wrapper_host: str,
) -> Dict[str, Any]:
    ca_container = "/tmp/infinito/ca/root-ca.crt"
    wrapper_container = "/tmp/infinito/bin/with-ca-trust.sh"

    out_services: Dict[str, Any] = {}

    for name, svc in services.items():
        if not isinstance(svc, dict):
            die(f"Service '{name}' must be a mapping in compose config")

        cmd_list = normalize_cmd(svc.get("command"))
        if cmd_list:
            effective_cmd = cmd_list
        else:
            image = svc.get("image")
            if not isinstance(image, str) or not image.strip():
                die(f"Service '{name}' has no command and no image in composed config")
            ep, img_cmd = docker_image_inspect(image.strip(), cwd=cwd, env=env)
            effective_cmd = ep + img_cmd
            if not effective_cmd:
                die(f"Service '{name}' resolved to empty command from image '{image}'")

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

    env = dict(**__import__("os").environ)

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

    cmd = ["docker", "compose", "-p", str(args.project)] + parts
    if env_file:
        cmd += ["--env-file", str(args.env_file)]
    cmd += ["config"]

    rc, out, err = run(cmd, cwd=cwd, env=env)
    if rc != 0:
        die(f"docker compose config failed (rc={rc}): {err.strip()}")

    doc = parse_yaml(out, "docker compose config output")
    services = doc.get("services")
    if not isinstance(services, dict) or not services:
        die(
            "docker compose config output must contain non-empty mapping at top-level key 'services'"
        )

    override_doc = render_override(
        services, cwd=cwd, env=env, ca_host=ca_host, wrapper_host=wrapper_host
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
