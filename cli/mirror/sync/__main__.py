from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from cli.mirror.providers import GHCRProvider
from cli.mirror.util import iter_role_images


def _validate_positive_int(value: str) -> int:
    try:
        n = int(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError("must be an integer") from e
    if n <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return n


def _throttle_before_next_copy(
    *, images_per_hour: Optional[int], last_start_ts: Optional[float]
) -> float:
    """
    If images_per_hour is set, ensure at least (3600 / images_per_hour) seconds
    have elapsed since last_start_ts before returning.

    Returns the (possibly updated) start timestamp for the next copy.
    """
    if not images_per_hour:
        return time.monotonic()

    min_interval = 3600.0 / float(images_per_hour)
    now = time.monotonic()

    if last_start_ts is not None:
        elapsed = now - last_start_ts
        remaining = min_interval - elapsed
        if remaining > 0:
            print(
                f"[mirror] throttling: sleeping {remaining:.1f}s "
                f"(limit={images_per_hour} images/hour)",
                flush=True,
            )
            time.sleep(remaining)

    return time.monotonic()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ghcr-namespace", required=True)
    parser.add_argument("--ghcr-prefix", default="mirror")
    parser.add_argument(
        "--images-per-hour",
        type=_validate_positive_int,
        default=None,
        help="Optional throttle: max images to mirror per hour (best-effort).",
    )
    args = parser.parse_args()

    provider = GHCRProvider(args.ghcr_namespace, args.ghcr_prefix)
    repo_root = Path(args.repo_root).resolve()

    failures: List[str] = []
    total = 0

    last_start_ts: Optional[float] = None

    for img in iter_role_images(repo_root):
        # Optional throttling (only when --images-per-hour is set)
        last_start_ts = _throttle_before_next_copy(
            images_per_hour=args.images_per_hour,
            last_start_ts=last_start_ts,
        )

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
            print(
                f"[mirror] {label}: FAILED, continuing...",
                file=sys.stderr,
                flush=True,
            )
        except Exception as e:
            msg = f"{label}: FAILED (unexpected error: {e!r})"
            failures.append(msg)
            print(
                f"[mirror] {label}: FAILED (unexpected), continuing...",
                file=sys.stderr,
                flush=True,
            )

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
