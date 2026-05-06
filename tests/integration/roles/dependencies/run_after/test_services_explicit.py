"""Integration guard: every role listed under another role's
``meta/services.yml.<entity>.run_after`` MUST also be pulled in
explicitly via that role's own services block.

Future direction: the inventory builder is moving away from
``run_after`` as a dependency-injection mechanism. ``run_after`` keeps
its ordering-only role; "what gets co-deployed with this role" is
decided by the per-role ``services`` map. This test catches roles
whose ``run_after`` smuggles a dep in that no ``services.<key>``
entry covers.

Accepted shapes per ``run_after`` entry ``Y``:

1. The consuming role declares ``services.<key>`` where ``<key>`` is
   the primary service key for ``Y`` in the project-wide service
   registry, with ``enabled: true`` AND ``shared: true``.
2. Or the same entry, with ``enabled`` / ``shared`` set to a Jinja
   conditional containing ``in group_names`` (e.g.
   ``"{{ 'web-app-foo' in group_names }}"``). The Jinja form lets a
   role conditionally pull a dep based on the live host's group
   membership while still encoding the dependency declaratively in
   ``services``.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from utils.roles.meta_lookup import get_role_run_after
from utils.service_registry import (
    build_role_to_primary_service_key,
    build_service_registry_from_roles_dir,
)


PROJECT_ROOT = Path(__file__).resolve().parents[5]
ROLES_DIR = PROJECT_ROOT / "roles"


# Service keys that transitively guarantee a run_after dep is co-deployed.
# When the consumer lists ``dep`` in ``run_after``, either the registry's
# primary service key for ``dep`` OR any of these equivalents counts as
# an explicit declaration.
#
# Example: ``run_after: [web-app-keycloak]`` is satisfied by
# ``services.oidc.enabled=true`` (direct) OR ``services.oauth2.enabled=true``
# (oauth2-proxy itself depends on Keycloak).
_TRANSITIVE_SERVICE_EQUIVALENTS: dict[str, set[str]] = {
    "web-app-keycloak": {"oidc", "oauth2"},
}


def _load_services(role_dir: Path) -> dict:
    services_file = role_dir / "meta" / "services.yml"
    if not services_file.is_file():
        return {}
    text = services_file.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def _flag_is_explicit_truth(value) -> bool:
    """Return True if a services flag (enabled/shared) is either the literal
    boolean ``True`` or a Jinja string containing ``in group_names``."""
    if value is True:
        return True
    if isinstance(value, str) and "in group_names" in value:
        return True
    return False


class TestRunAfterServicesExplicit(unittest.TestCase):
    def test_run_after_entries_have_matching_service_flag(self):
        registry = build_service_registry_from_roles_dir(ROLES_DIR)
        role_to_key = build_role_to_primary_service_key(registry)

        offenders: list[str] = []
        for role_dir in sorted(p for p in ROLES_DIR.iterdir() if p.is_dir()):
            role_name = role_dir.name
            try:
                run_after = get_role_run_after(role_dir, role_name=role_name)
            except Exception:
                continue
            if not run_after:
                continue

            services = _load_services(role_dir)

            for dep in run_after:
                primary_key = role_to_key.get(dep)
                seen: set[str] = set()
                candidate_keys: list[str] = []
                for key in (
                    [primary_key] if primary_key else []
                ) + sorted(_TRANSITIVE_SERVICE_EQUIVALENTS.get(dep, set())):
                    if key and key not in seen:
                        seen.add(key)
                        candidate_keys.append(key)

                if not candidate_keys:
                    offenders.append(
                        f"{role_name}: run_after entry '{dep}' is not a "
                        f"service provider in the registry; either drop it "
                        f"from run_after or have '{dep}' export a shared "
                        f"service entity."
                    )
                    continue

                # A single legitimate entry is enough.
                matched = False
                near_misses: list[str] = []
                for key in candidate_keys:
                    entry = services.get(key)
                    if not isinstance(entry, dict):
                        near_misses.append(f"services.{key}: missing")
                        continue
                    if _flag_is_explicit_truth(
                        entry.get("enabled")
                    ) and _flag_is_explicit_truth(entry.get("shared")):
                        matched = True
                        break
                    near_misses.append(
                        f"services.{key}: enabled={entry.get('enabled')!r}, "
                        f"shared={entry.get('shared')!r}"
                    )

                if not matched:
                    expected_options = " | ".join(
                        f"services.{k}" for k in candidate_keys
                    )
                    offenders.append(
                        f"{role_name}: run_after lists '{dep}' but no "
                        f"matching enabled+shared entry in {expected_options}. "
                        f"Found: " + "; ".join(near_misses) + ". "
                        f"Declare one of those with enabled=true (or "
                        f"\"{{{{ '{dep}' in group_names }}}}\") and "
                        f"shared=true."
                    )

        if offenders:
            self.fail(
                "Implicit dependencies pulled via run_after only (req: every "
                "run_after entry must be matched by an explicit services "
                "flag):\n" + "\n".join(f"  - {o}" for o in offenders)
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
