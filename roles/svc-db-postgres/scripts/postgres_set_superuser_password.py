#!/usr/bin/env python3
"""
Set the PostgreSQL superuser ('postgres') password inside a Docker container.

Exit codes:
  0 = no change (password already valid)
  2 = changed (password was updated)
  1 = error
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import List


def run(cmd: List[str], env: dict | None = None, input_text: str | None = None):
    return subprocess.run(
        cmd,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )


def password_works(container: str, user: str, db: str, password: str) -> bool:
    cmd = [
        "docker",
        "exec",
        "-e",
        f"PGPASSWORD={password}",
        container,
        "psql",
        "-U",
        user,
        "-d",
        db,
        "-c",
        "SELECT 1",
    ]
    return run(cmd).returncode == 0


def set_password(container: str, user: str, db: str, password: str) -> None:
    sql = "ALTER USER postgres WITH PASSWORD :'new_password';\n"

    cmd = [
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-U",
        user,
        "-d",
        db,
        "-v",
        "ON_ERROR_STOP=1",
        "-v",
        f"new_password={password}",
    ]

    proc = run(cmd, input_text=sql)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ensure postgres superuser password inside a Docker container."
    )
    parser.add_argument("--container", required=True)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--db", default="postgres")
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    try:
        if password_works(args.container, args.user, args.db, args.password):
            print("postgres password already valid")
            return 0

        set_password(args.container, args.user, args.db, args.password)

        print("postgres password updated")
        return 2

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
