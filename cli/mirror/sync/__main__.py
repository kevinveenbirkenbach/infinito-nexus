from __future__ import annotations
import argparse
from pathlib import Path

from cli.mirror.util import iter_role_images
from cli.mirror.providers import GHCRProvider


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ghcr-namespace", required=True)
    parser.add_argument("--ghcr-prefix", default="mirror")
    args = parser.parse_args()

    provider = GHCRProvider(args.ghcr_namespace, args.ghcr_prefix)
    repo_root = Path(args.repo_root).resolve()

    for img in iter_role_images(repo_root):
        provider.mirror(img)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
