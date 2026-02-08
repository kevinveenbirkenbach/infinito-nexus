from __future__ import annotations

from pathlib import Path

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


def _ensure_ruamel_map(node: CommentedMap, key: str) -> CommentedMap:
    if key not in node or not isinstance(node.get(key), CommentedMap):
        node[key] = CommentedMap()
    return node[key]


def _is_blank(val: object) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        return not val.strip()
    return False


def _get_policy(svc_doc: CommentedMap) -> str:
    """
    Read mirror policy from existing host_vars service node.
    Allowed: force | skip | if_missing
    Default: if_missing
    """
    raw = svc_doc.get("mirror_policy")
    if raw is None:
        return "if_missing"
    if not isinstance(raw, str):
        return "if_missing"
    policy = raw.strip().lower()
    if policy in {"force", "skip", "if_missing"}:
        return policy
    return "if_missing"


def apply_mirror_overrides(host_vars_file: Path, mirrors_file: Path) -> None:
    """
    Apply compose image mirror overrides to host_vars.

    Mirrors file format (YAML or JSON):
      applications:
        <app_id>:
          compose:
            services:
              <svc>:
                image: <new-image-base>
                version: <tag>

    Behavior / precedence:
      - By default, manual values in host_vars win.
      - mirror_policy in host_vars service node controls how mirror applies:
          - force     -> always overwrite image/version
          - skip      -> never change image/version
          - if_missing(default) -> only fill missing/blank image/version
      - If app/service does not exist in host_vars, it will be created and mirror values applied.
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

        docker = app_block.get("compose") or {}
        if not isinstance(docker, dict):
            continue

        services = docker.get("services") or {}
        if not isinstance(services, dict):
            continue

        app_doc = _ensure_ruamel_map(apps_doc, str(app_id))
        docker_doc = _ensure_ruamel_map(app_doc, "compose")
        services_doc = _ensure_ruamel_map(docker_doc, "services")

        for svc_name, svc_block in services.items():
            if not isinstance(svc_block, dict):
                continue

            image = svc_block.get("image")
            version = svc_block.get("version")

            if not isinstance(image, str) or _is_blank(image):
                continue
            if not isinstance(version, str) or _is_blank(version):
                continue

            svc_doc = _ensure_ruamel_map(services_doc, str(svc_name))

            # policy only comes from existing host_vars service node
            policy = _get_policy(svc_doc)

            if policy == "skip":
                continue

            if policy == "force":
                svc_doc["image"] = image.strip()
                svc_doc["version"] = version.strip()
                applied += 1
                continue

            # if_missing (default)
            if _is_blank(svc_doc.get("image")):
                svc_doc["image"] = image.strip()
                applied += 1
            if _is_blank(svc_doc.get("version")):
                svc_doc["version"] = version.strip()
                applied += 1

    if applied <= 0:
        return

    host_vars_file.parent.mkdir(parents=True, exist_ok=True)
    with host_vars_file.open("w", encoding="utf-8") as f:
        yaml_rt.dump(doc, f)
