"""Application-only role artefacts.

Some files inside ``roles/<role>/meta/`` only carry meaning when the
role declares an ``application_id`` in ``vars/main.yml`` and is therefore
deployable as a primary app via ``--apps``. This module holds the
canonical mapping of such files plus a lightweight predicate that
recognises whether a role is an application role.

Lint tests under ``tests/integration/roles/meta/`` use the mapping to
forbid app-only artefacts on non-app roles, and the variant-coverage
lint uses :func:`is_application_role` so its scope tracks the same
boundary as the matrix-deploy planner.
"""

from __future__ import annotations

from pathlib import Path

from utils.cache.yaml import load_yaml_any

# Files inside ``roles/<role>/meta/`` that only make sense for roles
# declaring an ``application_id``. The descriptions explain why the file
# is restricted so a contributor reading the lint failure understands
# the reason without chasing back to commit history.
APPLICATION_ONLY_META_FILES: dict[str, str] = {
    "server.yml": (
        "Server-side compose attributes (CSP, domains, status codes). "
        "Only meaningful when the role exposes a deployable HTTP service."
    ),
    "rbac.yml": (
        "Role-based access control declarations for the application's "
        "Keycloak realm and oauth2 layer."
    ),
    "volumes.yml": (
        "Compose volume declarations for the application's container stack."
    ),
    "variants.yml": (
        "Matrix-deploy variant overrides. Only iterated for primary apps "
        "addressable via ``--apps``."
    ),
    "schema.yml": (
        "Application config schema describing credentials and validation rules."
    ),
}


def is_application_role(role_dir: Path) -> bool:
    """Return ``True`` when *role_dir* declares a non-empty
    ``application_id`` in ``vars/main.yml``.

    A missing ``vars/main.yml``, a malformed root, or an empty / non-string
    ``application_id`` all map to ``False`` so callers may use this
    predicate as a coarse "is this role app-targetable" filter without
    tripping on partially-migrated roles.
    """
    vars_path = role_dir / "vars" / "main.yml"
    if not vars_path.is_file():
        return False
    data = load_yaml_any(str(vars_path), default_if_missing={}) or {}
    if not isinstance(data, dict):
        return False
    app_id = data.get("application_id")
    return isinstance(app_id, str) and bool(app_id.strip())
