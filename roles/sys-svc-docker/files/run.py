#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def die(msg: str, code: int = 2) -> "None":
    print(f"[run] {msg}", file=sys.stderr)
    raise SystemExit(code)


def must_exist(path: str, label: str) -> str:
    p = Path(path)
    if not p.exists():
        die(f"{label} does not exist: {path}")
    return str(p)


FLAGS_TAKE_VALUE = {
    "-e",
    "--env",
    "--env-file",
    "--network",
    "--name",
    "-v",
    "--volume",
    "-u",
    "--user",
    "-w",
    "--workdir",
    "--entrypoint",
    "-p",
    "--publish",
    "--security-opt",
    "--add-host",
    "--dns",
    "--dns-search",
    "--dns-option",
    "--label",
    "-l",
    "--hostname",
    "-h",
    "--platform",
    "--restart",
    "--pull",
    "--runtime",
    "--ipc",
    "--pid",
    "--cap-add",
    "--cap-drop",
    "--mount",
    "--gpus",
    "--group-add",
    "--shm-size",
    "--stop-timeout",
    "--stop-signal",
    "--log-driver",
    "--log-opt",
}


def split_docker_run_argv(argv: List[str]) -> Tuple[List[str], List[str]]:
    """
    Split argv into:
      - run_opts: docker run options (everything before IMAGE)
      - image_and_args: [IMAGE, ...ARGS]
    """
    if not argv:
        die("Usage: run [docker-run-flags...] IMAGE [COMMAND/ARGS...]")

    run_opts: List[str] = []
    i = 0

    while i < len(argv):
        a = argv[i]

        if a == "--":
            run_opts.append(a)
            i += 1
            break

        if a.startswith("-"):
            run_opts.append(a)
            if a in FLAGS_TAKE_VALUE:
                i += 1
                if i >= len(argv):
                    die(f"docker run flag requires a value: {a}")
                run_opts.append(argv[i])
            i += 1
            continue

        break

    if i >= len(argv):
        die("Missing IMAGE argument")

    return run_opts, argv[i:]


def extract_entrypoint(run_opts: List[str]) -> Tuple[List[str], Optional[str]]:
    """
    Remove --entrypoint from run_opts and return (new_opts, entrypoint_value).
    Supports:
      --entrypoint sh
      --entrypoint=sh
    """
    out: List[str] = []
    entrypoint: Optional[str] = None
    i = 0

    while i < len(run_opts):
        a = run_opts[i]

        if a == "--entrypoint":
            if i + 1 >= len(run_opts):
                die("--entrypoint requires a value")
            entrypoint = run_opts[i + 1]
            i += 2
            continue

        if a.startswith("--entrypoint="):
            entrypoint = a.split("=", 1)[1]
            i += 1
            continue

        out.append(a)
        i += 1

    return out, entrypoint


def inspect_image_entrypoint(image: str) -> List[str]:
    """
    Return image Config.Entrypoint as a list. If not set, returns [].
    """
    try:
        p = subprocess.run(
            [
                "docker",
                "image",
                "inspect",
                image,
                "--format",
                "{{json .Config.Entrypoint}}",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        die("docker not found. Please install Docker.", code=127)

    if p.returncode != 0:
        die(f"docker image inspect failed for {image}: {p.stderr.strip()}", code=2)

    raw = (p.stdout or "").strip()
    if raw in ("", "null", "None"):
        return []
    try:
        val = json.loads(raw)
    except Exception:
        return []
    if isinstance(val, list):
        return [str(x) for x in val]
    if isinstance(val, str) and val:
        return [val]
    return []


def main() -> int:
    argv = sys.argv[1:]
    debug = False
    if "--debug" in argv:
        debug = True
        argv = [a for a in argv if a != "--debug"]

    ca_host = os.environ.get("CA_TRUST_CERT_HOST", "").strip()
    wrapper_host = os.environ.get("CA_TRUST_WRAPPER_HOST", "").strip()
    trust_name = os.environ.get("CA_TRUST_NAME", "").strip()

    if not ca_host:
        die("Missing env CA_TRUST_CERT_HOST")
    if not wrapper_host:
        die("Missing env CA_TRUST_WRAPPER_HOST")
    if not trust_name:
        die("Missing env CA_TRUST_NAME")

    ca_host = must_exist(ca_host, "CA trust certificate")
    wrapper_host = must_exist(wrapper_host, "CA trust wrapper script")

    run_opts, image_and_args = split_docker_run_argv(argv)
    run_opts, user_entrypoint = extract_entrypoint(run_opts)

    image = image_and_args[0]
    user_args = image_and_args[1:]  # might be empty, might start with --short, etc.

    ca_container = "/tmp/infinito/ca/root-ca.crt"
    wrapper_container = "/tmp/infinito/bin/with-ca-trust.sh"

    inject_opts: List[str] = [
        "-v",
        f"{ca_host}:{ca_container}:ro",
        "-v",
        f"{wrapper_host}:{wrapper_container}:ro",
        "-e",
        f"CA_TRUST_CERT={ca_container}",
        "-e",
        f"CA_TRUST_NAME={trust_name}",
        "--entrypoint",
        wrapper_container,
    ]

    final_cmd: List[str] = ["docker", "run"]
    final_cmd.extend(run_opts)
    final_cmd.extend(inject_opts)
    final_cmd.append(image)

    # Determine what command to run under with-ca-trust:
    # - if user provided --entrypoint X: run X ...
    # - else: emulate docker run semantics by using image ENTRYPOINT (if any)
    if user_entrypoint:
        final_cmd.append(user_entrypoint)
        final_cmd.extend(user_args)
    else:
        ep = inspect_image_entrypoint(image)
        if not ep:
            die(
                "Image has no ENTRYPOINT and you did not pass --entrypoint. "
                "Cannot determine executable to run under CA wrapper."
            )
        final_cmd.extend(ep)
        final_cmd.extend(user_args)

    if debug:
        print(">>> " + " ".join(shlex.quote(x) for x in final_cmd), file=sys.stderr)

    os.execvp(final_cmd[0], final_cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
