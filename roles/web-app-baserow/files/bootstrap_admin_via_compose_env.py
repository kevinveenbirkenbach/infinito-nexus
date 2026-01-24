#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys


BOOTSTRAP_CODE = r"""
import os
from django.contrib.auth import get_user_model

username = os.environ["BOOTSTRAP_ADMIN_USERNAME"]
email = os.environ["BOOTSTRAP_ADMIN_EMAIL"]
password = os.environ["BOOTSTRAP_ADMIN_PASSWORD"]

User = get_user_model()

u, created = User.objects.get_or_create(
    username=username,
    defaults={"email": email, "is_staff": True, "is_superuser": True},
)

if created:
    u.set_password(password)
    u.save()

print("created" if created else "exists")
""".strip()


def must(name: str) -> str:
    v = os.environ.get(name, "")
    if not v:
        raise SystemExit(f"Missing required env var: {name}")
    return v


def run(cmd: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def main() -> int:
    compose_dir = must("BASEROW_COMPOSE_DIR")
    env_file = must("BASEROW_COMPOSE_ENV_FILE")
    service = must("BASEROW_SERVICE_NAME")

    python_bin = must("BASEROW_PYTHON_BIN")
    manage_py = must("BASEROW_MANAGE_PY")

    settings_module = must("BASEROW_DJANGO_SETTINGS_MODULE")
    secret_key = must("BASEROW_SECRET_KEY")

    admin_username = must("BASEROW_BOOTSTRAP_ADMIN_USERNAME")
    admin_email = must("BASEROW_BOOTSTRAP_ADMIN_EMAIL")
    admin_password = must("BASEROW_BOOTSTRAP_ADMIN_PASSWORD")

    cmd = [
        "docker",
        "compose",
        "--env-file",
        env_file,
        "exec",
        "-T",
        "-e",
        f"DJANGO_SETTINGS_MODULE={settings_module}",
        "-e",
        f"SECRET_KEY={secret_key}",
        "-e",
        f"BASEROW_SECRET_KEY={secret_key}",
        "-e",
        f"BOOTSTRAP_ADMIN_USERNAME={admin_username}",
        "-e",
        f"BOOTSTRAP_ADMIN_EMAIL={admin_email}",
        "-e",
        f"BOOTSTRAP_ADMIN_PASSWORD={admin_password}",
        service,
        python_bin,
        manage_py,
        "shell",
        "-c",
        BOOTSTRAP_CODE,
    ]

    proc = run(cmd, cwd=compose_dir)

    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
