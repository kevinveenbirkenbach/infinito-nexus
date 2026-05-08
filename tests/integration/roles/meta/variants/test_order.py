"""Lint guard: variants of an application MUST agree on the recursive
set of dep roles they pull in.

Background
==========
The matrix-deploy mechanism (docs/contributing/design/variants.md)
keeps prior-round state alive between rounds: a role whose variant did
not change is left running at whatever state the previous round
produced. If variant 0 of role A pulls in role B via shared-service
auto-include but variant 1 of A does not, then a later round running
A's variant 1 inherits a leftover B from the previous round — host
state contradicts the variant's intent and tasks like
``sys-svc-mail/01_core.yml`` make wrong decisions because their gating
(``email.external``, group_names) reflects the per-play view while the
host carries cross-play residue.

This lint forces every variant of an application to agree on its
recursive dep closure (run_after + shared-service auto-include) so
round-to-round transitions stay state-consistent.

Detection
=========
For each application with ``len(variants) > 1``:

1. Compute ``closure_v = transitive set of role IDs`` reachable from
   the application via ``run_after`` plus shared-service auto-include
   (``services.<svc>.enabled is True AND shared is True``), using
   variant ``v`` for the application's own services and variant 0 for
   every recursive dep (deps don't track the parent's variant).
2. Drop variants whose closure is empty (minimal/standalone variants
   that intentionally disable every dep-pulling service drop out of
   the dep ordering and cannot disagree with anything).
3. If any two of the remaining (non-empty) closures differ, record
   the divergence as an offender.
"""

from __future__ import annotations

import contextlib
import unittest
from pathlib import Path
from typing import Any

from utils.cache.applications import get_variants
from utils.roles.applications.services.registry import (
    build_service_registry_from_applications,
    load_run_after_from_roles_dir,
    resolve_service_dependency_roles_from_config,
)

from . import PROJECT_ROOT

ROLES_DIR: Path = PROJECT_ROOT / "roles"


def _direct_deps(
    role: str,
    config: dict[str, Any],
    registry: dict[str, dict[str, Any]],
    roles_dir: Path,
) -> set[str]:
    deps = set(resolve_service_dependency_roles_from_config(config, registry))
    # Shape errors in run_after are caught by their own lint; here we
    # treat the role as having no run_after so this lint stays focused
    # on variant divergence.
    with contextlib.suppress(Exception):
        deps.update(load_run_after_from_roles_dir(roles_dir, role))
    return deps


def _closure(
    role: str,
    config: dict[str, Any],
    registry: dict[str, dict[str, Any]],
    roles_dir: Path,
    variants_by_app: dict[str, list[Any]],
) -> frozenset[str]:
    visited: set[str] = set()
    stack: list[tuple[str, dict[str, Any]]] = [(role, config)]
    while stack:
        current_role, current_config = stack.pop()
        for dep in _direct_deps(current_role, current_config, registry, roles_dir):
            if dep == role or dep in visited:
                continue
            visited.add(dep)
            dep_variants = variants_by_app.get(dep)
            dep_config = dep_variants[0] if dep_variants else {}
            stack.append((dep, dep_config))
    return frozenset(visited)


class TestVariantDepConsistency(unittest.TestCase):
    """All variants of an application MUST resolve to the same dep closure."""

    def test_variants_agree_on_dep_closure(self) -> None:
        variants_by_app = get_variants(roles_dir=str(ROLES_DIR))

        # Service registry is built from variant 0 of every app — this
        # is the canonical view used to resolve which role a service
        # key points to. Variant overrides can flip enabled/shared but
        # cannot change what role provides a given service key.
        defaults = {
            app: variants[0] for app, variants in variants_by_app.items() if variants
        }
        registry = build_service_registry_from_applications(defaults)

        offenders: dict[str, list[tuple[int, list[str]]]] = {}
        for app, variants in sorted(variants_by_app.items()):
            if len(variants) <= 1:
                continue
            closures = [
                _closure(app, variant, registry, ROLES_DIR, variants_by_app)
                for variant in variants
            ]
            # Variants whose closure is empty intentionally drop out of
            # the dep ordering (minimal/standalone variants that disable
            # every dep-pulling service). They cannot disagree with
            # anything, so only non-empty closures are compared.
            non_empty = [closure for closure in closures if closure]
            if non_empty and any(closure != non_empty[0] for closure in non_empty[1:]):
                offenders[app] = [
                    (index, sorted(closure)) for index, closure in enumerate(closures)
                ]

        if not offenders:
            return

        lines = [
            f"{len(offenders)} application(s) carry variants that disagree on "
            "their recursive dep closure (run_after + shared-service "
            "auto-include). Variants MUST resolve to the same set of "
            "transitively-included roles, otherwise round-to-round "
            "matrix-deploy transitions leave inconsistent host state.",
            "",
            "Background: docs/contributing/design/variants.md",
            "",
        ]
        for app, items in sorted(offenders.items()):
            lines.append(f"  - {app}:")
            for index, closure in items:
                rendered = ", ".join(closure) if closure else "(empty)"
                lines.append(f"      * variant {index}: {rendered}")
        self.fail("\n".join(lines))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
