from __future__ import annotations
import argparse
import json
from pathlib import Path
import yaml

from cli.mirror.util import iter_role_images
from cli.mirror.providers import GHCRProvider


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ghcr-namespace", required=True)
    parser.add_argument("--ghcr-prefix", default="mirror")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    provider = GHCRProvider(args.ghcr_namespace, args.ghcr_prefix)
    repo_root = Path(args.repo_root).resolve()

    applications = {}

    for img in iter_role_images(repo_root):
        app = applications.setdefault(img.role, {})
        docker = app.setdefault("compose", {})
        services = docker.setdefault("services", {})

        services[str(img.service)] = {
            "image": provider.image_base(img),
            "version": img.version,
        }

    result = {"applications": applications}

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(yaml.safe_dump(result, sort_keys=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
