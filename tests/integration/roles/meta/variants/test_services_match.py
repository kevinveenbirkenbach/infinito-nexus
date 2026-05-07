"""Integration guard: every service key referenced under ``services:``
in a role's `meta/variants.yml` MUST exist as a top-level key in the
same role's `meta/services.yml`.

Why
---

The matrix-deploy CLI deep-merges each variant onto the role's
`meta/services.yml` to produce one effective `applications.<role>`
config per variant entry. Keys that exist in `variants.yml` but NOT
in `services.yml` survive the merge as dead config — at best a typo
that silently does nothing, at worst a stale reference to a service
that was renamed or removed (and now silently fails to flip its
flags). Either way the variant promises coverage for a service the
role does not actually declare.

This test catches that drift early. The check is intentionally
asymmetric: extra keys in `services.yml` (services declared but not
overridden by any variant) are fine and tracked by
[test_variants_coverage.py](./test_variants_coverage.py); only the
opposite direction (variant overrides → services declared) is what
this guard enforces.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import List

from utils.cache.yaml import load_yaml_any


from . import PROJECT_ROOT

ROLES_DIR = PROJECT_ROOT / "roles"


def _load_yaml(path: Path) -> object:
    if not path.is_file():
        return None
    try:
        return load_yaml_any(str(path), default_if_missing=None)
    except Exception:
        return None


class TestVariantsServicesMatch(unittest.TestCase):
    def test_variants_only_reference_services_declared_in_services_yml(self):
        offenders: List[str] = []

        for role_dir in sorted(p for p in ROLES_DIR.iterdir() if p.is_dir()):
            role_name = role_dir.name
            services = _load_yaml(role_dir / "meta" / "services.yml")
            if not isinstance(services, dict):
                continue
            declared_keys = {k for k in services.keys() if isinstance(k, str)}

            variants_raw = _load_yaml(role_dir / "meta" / "variants.yml")
            if not isinstance(variants_raw, list):
                continue

            for index, variant in enumerate(variants_raw):
                if not isinstance(variant, dict):
                    continue
                variant_services = variant.get("services")
                if not isinstance(variant_services, dict):
                    continue
                for key in variant_services.keys():
                    if not isinstance(key, str):
                        continue
                    if key in declared_keys:
                        continue
                    offenders.append(
                        f"{role_name}: variants.yml[{index}].services.{key} "
                        f"is not declared as a top-level key in "
                        f"meta/services.yml. Either add ``{key}:`` to "
                        f"services.yml or drop the override from this "
                        f"variant entry."
                    )

        if offenders:
            self.fail(
                "variants.yml references services not declared in "
                "services.yml:\n" + "\n".join(f"  - {o}" for o in offenders)
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
