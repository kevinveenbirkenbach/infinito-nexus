"""Lint compose service resource limits in role configs.

Every role's primary compose service (``services.<entity_name>``)
should declare the host-resource guard rails:

- ``min_storage``
- ``cpus``
- ``mem_reservation``
- ``mem_limit``
- ``pids_limit``

Missing keys currently emit one ``::warning`` annotation each so CI highlights
them without blocking merges. When every role has caught up the test flips to
failing: that is the signal to switch this rule from warn-only to strict mode
(convert the warnings into assertions).
"""

from __future__ import annotations

import re
import unittest
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

from utils.annotations.message import in_github_actions, warning
from utils.cache.files import read_text
from utils.cache.yaml import load_yaml_any
from utils.roles.entity_name import get_entity_name
from utils.roles.mapping import ROLE_FILE_META_SERVICES

from . import PROJECT_ROOT

if TYPE_CHECKING:
    from pathlib import Path

REQUIRED_KEYS = (
    "min_storage",
    "cpus",
    "mem_reservation",
    "mem_limit",
    "pids_limit",
)


@dataclass(frozen=True)
class MissingKeyFinding:
    role: str
    service: str
    key: str
    config_path: Path
    line: int


def _load_yaml(path: Path) -> dict:
    try:
        data = load_yaml_any(str(path), default_if_missing={})
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


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
        # Best-effort lookup only: if the file can't be read, keep linting and
        # point the annotation at line 1 as a safe fallback.
        return 1
    return 1


def _collect_findings(root: Path) -> list[MissingKeyFinding]:
    findings: list[MissingKeyFinding] = []
    roles_dir = root / "roles"
    for role_dir in sorted(roles_dir.iterdir()):
        if not role_dir.is_dir():
            continue
        config_path = role_dir / ROLE_FILE_META_SERVICES
        if not config_path.is_file():
            continue

        # Post-req-008: meta/services.yml's root IS the services map; the
        # legacy `compose.services` wrapper no longer exists.
        services = _load_yaml(config_path)
        if not isinstance(services, dict):
            continue

        entity_name = get_entity_name(role_dir.name)
        if not entity_name or entity_name not in services:
            continue
        primary_conf = services.get(entity_name)
        if not isinstance(primary_conf, dict):
            continue
        if primary_conf.get("shared") is True:
            continue

        service_line = _find_service_line(config_path, entity_name)
        findings.extend(
            MissingKeyFinding(
                role=role_dir.name,
                service=entity_name,
                key=key,
                config_path=config_path,
                line=service_line,
            )
            for key in REQUIRED_KEYS
            if key not in primary_conf
        )

    findings.sort(key=lambda f: (f.role, f.service, f.key))
    return findings


def _emit_warning(finding: MissingKeyFinding, root: Path) -> None:
    rel = finding.config_path.relative_to(root).as_posix()
    warning(
        f"{finding.role}: services.{finding.service}.{finding.key} is not set",
        title="Missing resource limit",
        file=rel,
        line=finding.line,
    )


def _print_summary(findings: list[MissingKeyFinding], root: Path) -> None:
    if not findings:
        return
    print()
    print(f"[WARNING] Missing compose-service resource limits ({len(findings)}):")
    for f in findings:
        rel = f.config_path.relative_to(root).as_posix()
        print(f"- {rel}:{f.line} - services.{f.service}.{f.key} ({f.role})")


class TestComposeResourceLimits(unittest.TestCase):
    def test_primary_services_declare_resource_limits(self) -> None:
        """Warn per missing resource key on every role's primary compose service.
        Fails once nothing is missing so the rule gets flipped to strict mode.
        """
        root = PROJECT_ROOT
        findings = _collect_findings(root)

        for finding in findings:
            _emit_warning(finding, root)

        if not in_github_actions():
            _print_summary(findings, root)

        self.assertGreater(
            len(findings),
            0,
            "All primary compose services declare every required resource key "
            f"({', '.join(REQUIRED_KEYS)}). Switch this test from warn-only to "
            "strict mode: replace the `assertGreater` sentinel with "
            "`assertEqual(len(findings), 0, ...)` so future regressions fail "
            "the build instead of emitting warnings.",
        )


if __name__ == "__main__":
    unittest.main()
