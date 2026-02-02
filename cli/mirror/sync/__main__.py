from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List

from cli.mirror.providers import GHCRProvider
from cli.mirror.util import iter_role_images


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ghcr-namespace", required=True)
    parser.add_argument("--ghcr-prefix", default="mirror")
    args = parser.parse_args()

    provider = GHCRProvider(args.ghcr_namespace, args.ghcr_prefix)
    repo_root = Path(args.repo_root).resolve()

    failures: List[str] = []
    total = 0

    for img in iter_role_images(repo_root):
        total += 1
        src = f"docker://docker.io/{img.source}"
        dest = f"docker://{provider.image_base(img)}:{img.version}"
        label = f"{img.role}:{img.service} ({img.name}:{img.version})"

        try:
            print(f"[mirror] {label}: {src} -> {dest}", flush=True)
            provider.mirror(img)
        except subprocess.CalledProcessError as e:
            # keep going, but remember the failure
            msg = (
                f"{label}: FAILED (exit={e.returncode})\n"
                f"  cmd: {' '.join(map(str, e.cmd))}"
            )
            failures.append(msg)
            print(f"[mirror] {label}: FAILED, continuing...", file=sys.stderr, flush=True)
        except Exception as e:
            msg = f"{label}: FAILED (unexpected error: {e!r})"
            failures.append(msg)
            print(f"[mirror] {label}: FAILED (unexpected), continuing...", file=sys.stderr, flush=True)

    if failures:
        print("\n[mirror] SUMMARY: some images failed:", file=sys.stderr)
        for f in failures:
            print(f"- {f}", file=sys.stderr)
        print(f"\n[mirror] Result: {len(failures)}/{total} failed.", file=sys.stderr)
        return 1

    print(f"\n[mirror] Result: {total}/{total} succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
