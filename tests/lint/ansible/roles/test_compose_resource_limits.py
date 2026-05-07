"""Lint compose service resource limits in role configs.

Every Docker-service that a role declares for itself in
``meta/services.yml`` MUST set the host-resource guard rails:

- ``min_storage``
- ``cpus``
- ``mem_reservation``
- ``mem_limit``
- ``pids_limit``

Scope of the check:

1. Only roles that ship a ``templates/compose.yml.j2`` are scanned.
   Non-Docker roles (``desk-*``, ``dev-*``, ``drv-*``, ``pkgmgr*``,
   ``sys-*`` without a compose template, …) declare entries in their
   ``meta/services.yml`` for unrelated provisioning purposes; demanding
   container resource limits there has no operational meaning.

2. Inside the scanned roles, only the **self-declared** services are
   linted — the entries that this role actually defines as containers
   in its own compose file (entries that carry ``image`` / ``build`` /
   ``ports`` / ``volumes`` / etc.). Pure consumer markers
   (``services.<X>.enabled: true`` + ``shared: true`` and nothing
   else) point at a service the variant-aware planner pulls in from
   another role; the resource limits live on the **provider's**
   declaration, not on the marker. Aliases (entries with
   ``canonical:`` referencing the role's primary service) are also
   skipped because the resources are on the canonical entry they
   point to.

   Concretely: ``web-app-mailu/meta/services.yml.{mailu,email}`` are
   self-declared service entries (mailu's primary + its email alias
   provider) and MUST carry the resource keys; another role that
   imports email via ``services.email.enabled+shared: true`` is a
   consumer marker and MUST NOT be re-checked there.

The test fails the build on any missing key (no longer warn-only) so
regressions block CI.
"""

from __future__ import annotations

import re
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Mapping

import yaml

from utils.cache.files import read_text
from utils.cache.yaml import load_yaml_str
from utils.entity_name_utils import get_entity_name


REQUIRED_KEYS = (
    "min_storage",
    "cpus",
    "mem_reservation",
    "mem_limit",
    "pids_limit",
)


# Keys that mark an entry as a real Docker-service declaration. If any
# of these is set on the entry, we expect resource limits next to it.
SUBSTANTIVE_SERVICE_KEYS = frozenset(
    {
        "image",
        "build",
        "name",
        "ports",
        "volumes",
        "command",
        "entrypoint",
        "environment",
        "depends_on",
    }
)


def repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise AssertionError("Repository root not found from test path.")


@dataclass(frozen=True)
class MissingKeyFinding:
    role: str
    service: str
    key: str
    config_path: Path
    line: int


def _load_yaml(path: Path) -> dict:
    try:
        data = load_yaml_str(read_text(str(path)))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _is_self_declared_service(entry: Any, role_dir: Path, service_name: str) -> bool:
    """True iff *entry* is a service this role declares itself in its
    own compose file (and therefore owns the resource limits).

    Excluded:
    - Non-mapping entries (raw lists / scalars).
    - Aliases pointing at the role's primary entity via
      ``canonical: <primary>``. The resource limits live on the
      canonical entry.
    - Consumer markers (only ``enabled``/``shared``/``lifecycle`` set)
      that pull a service in from a provider role.

    Heuristic: substantive Docker-config keys
    (``image``/``build``/``ports``/``volumes``/``command``/...) are
    only present on actual service declarations.
    """
    if not isinstance(entry, Mapping):
        return False
    if "canonical" in entry:
        return False
    return any(
        k in entry for k in SUBSTANTIVE_SERVICE_KEYS
    ) or _is_primary_with_run_after(entry, role_dir, service_name)


def _is_primary_with_run_after(
    entry: Mapping[str, Any], role_dir: Path, service_name: str
) -> bool:
    """Edge case: a role's primary service entity occasionally only
    carries provisioning metadata (``run_after``, ``backup``,
    ``lifecycle``, …) and delegates the actual ``image`` to a Dockerfile
    in ``files/Dockerfile``. Treat the primary entity as self-declared
    if its name matches the role's entity name AND a Dockerfile / build
    template / compose template that builds it is present.
    """
    if get_entity_name(role_dir.name) != service_name:
        return False
    return (role_dir / "files" / "Dockerfile").is_file() or (
        role_dir / "templates" / "Dockerfile.j2"
    ).is_file()


def _find_service_line(config_path: Path, service_name: str) -> int:
    """1-based line of ``<service_name>:`` at the root of meta/services.yml.
    Falls back to 1 when unparsable so the annotation still points at the file.
    """
    pattern = re.compile(rf"^{re.escape(service_name)}\s*:\s*$")
    try:
        for i, raw in enumerate(read_text(str(config_path)).splitlines(), start=1):
            if pattern.match(raw):
                return i
    except OSError:
        return 1
    return 1


def _collect_findings(root: Path) -> List[MissingKeyFinding]:
    findings: List[MissingKeyFinding] = []
    roles_dir = root / "roles"
    for role_dir in sorted(roles_dir.iterdir()):
        if not role_dir.is_dir():
            continue
        # Filter 1: only roles that ship a compose.yml.j2 are Docker
        # roles whose service entries map to real containers.
        if not (role_dir / "templates" / "compose.yml.j2").is_file():
            continue

        config_path = role_dir / "meta" / "services.yml"
        if not config_path.is_file():
            continue

        # Post-req-008: meta/services.yml's root IS the services map.
        services = _load_yaml(config_path)
        if not isinstance(services, dict):
            continue

        # Filter 2: only entries this role declares itself.
        for service_name, service_conf in services.items():
            if not _is_self_declared_service(service_conf, role_dir, service_name):
                continue
            line = _find_service_line(config_path, service_name)
            for key in REQUIRED_KEYS:
                if key not in service_conf:
                    findings.append(
                        MissingKeyFinding(
                            role=role_dir.name,
                            service=service_name,
                            key=key,
                            config_path=config_path,
                            line=line,
                        )
                    )

    findings.sort(key=lambda f: (f.role, f.service, f.key))
    return findings


class TestComposeResourceLimits(unittest.TestCase):
    def test_self_declared_services_set_resource_limits(self) -> None:
        """Every self-declared service in a Docker role MUST set every
        ``REQUIRED_KEYS`` resource limit. Aliases and consumer markers
        are exempt — see the module docstring for the scope rules."""
        root = repo_root()
        findings = _collect_findings(root)

        if findings:
            grouped: dict[str, List[MissingKeyFinding]] = {}
            for f in findings:
                grouped.setdefault(f.role, []).append(f)
            lines = [
                f"{len(findings)} resource-limit declarations missing across "
                f"{len(grouped)} role(s):",
            ]
            for role, items in sorted(grouped.items()):
                rel = items[0].config_path.relative_to(root).as_posix()
                lines.append(f"  - {role} ({rel}):")
                for f in items:
                    lines.append(f"      services.{f.service}.{f.key} (line {f.line})")
            lines.append("")
            lines.append(
                "Add the missing keys (cpus / mem_reservation / mem_limit / "
                "min_storage / pids_limit) under each self-declared service "
                "entry in the role's meta/services.yml. Aliases (entries with "
                "`canonical: <primary>`) and consumer markers (just "
                "`enabled+shared`) are exempt."
            )
            self.fail("\n".join(lines))


if __name__ == "__main__":
    unittest.main()
