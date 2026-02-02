from __future__ import annotations

from pathlib import Path

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


def _ensure_ruamel_map(node: CommentedMap, key: str) -> CommentedMap:
    if key not in node or not isinstance(node.get(key), CommentedMap):
        node[key] = CommentedMap()
    return node[key]


def apply_mirror_overrides(host_vars_file: Path, mirrors_file: Path) -> None:
    """
    Overwrite applications.*.docker.services.*.{image,version} in host_vars
    based on a mirrors file.

    Mirrors file format (YAML or JSON):
      applications:
        <app_id>:
          docker:
            services:
              <svc>:
                image: <new-image-base>
                version: <tag>

    Only the keys present in mirrors_file are applied.
    """
    if not mirrors_file.exists():
        raise SystemExit(f"Mirrors file not found: {mirrors_file}")

    try:
        mirrors_raw = yaml.safe_load(mirrors_file.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise SystemExit(f"Failed to load mirrors file {mirrors_file}: {exc}") from exc

    if not isinstance(mirrors_raw, dict):
        raise SystemExit(
            f"Mirrors file must contain a mapping at top-level: {mirrors_file}"
        )

    mirrors_apps = mirrors_raw.get("applications", {}) or {}
    if not isinstance(mirrors_apps, dict) or not mirrors_apps:
        return  # no-op

    yaml_rt = YAML(typ="rt")
    yaml_rt.preserve_quotes = True

    if host_vars_file.exists():
        with host_vars_file.open("r", encoding="utf-8") as f:
            doc = yaml_rt.load(f)
        if doc is None:
            doc = CommentedMap()
    else:
        doc = CommentedMap()

    if not isinstance(doc, CommentedMap):
        tmp = CommentedMap()
        for k, v in dict(doc).items():
            tmp[k] = v
        doc = tmp

    apps_doc = _ensure_ruamel_map(doc, "applications")
    applied = 0

    for app_id, app_block in mirrors_apps.items():
        if not isinstance(app_block, dict):
            continue

        docker = app_block.get("docker") or {}
        if not isinstance(docker, dict):
            continue

        services = docker.get("services") or {}
        if not isinstance(services, dict):
            continue

        app_doc = _ensure_ruamel_map(apps_doc, str(app_id))
        docker_doc = _ensure_ruamel_map(app_doc, "docker")
        services_doc = _ensure_ruamel_map(docker_doc, "services")

        for svc_name, svc_block in services.items():
            if not isinstance(svc_block, dict):
                continue

            image = svc_block.get("image")
            version = svc_block.get("version")

            if not isinstance(image, str) or not image.strip():
                continue
            if not isinstance(version, str) or not version.strip():
                continue

            svc_doc = _ensure_ruamel_map(services_doc, str(svc_name))
            svc_doc["image"] = image.strip()
            svc_doc["version"] = version.strip()
            applied += 1

    if applied <= 0:
        return

    host_vars_file.parent.mkdir(parents=True, exist_ok=True)
    with host_vars_file.open("w", encoding="utf-8") as f:
        yaml_rt.dump(doc, f)
