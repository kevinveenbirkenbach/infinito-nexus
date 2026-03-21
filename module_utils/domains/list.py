#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _render_ansible_strict(
    *, raw: str, var_name: str, variables: dict[str, Any]
) -> str:
    from module_utils.templating import render_ansible_strict

    return render_ansible_strict(
        templar=None,
        raw=raw,
        var_name=var_name,
        err_prefix="domains.list",
        variables=variables,
    )


def _build_domain_index(applications: dict[str, Any]) -> dict[str, str]:
    from module_utils.domains.application_domain_index import build_domain_index

    return build_domain_index(applications)


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def render_domain_value(value: Any, variables: dict[str, Any], field_name: str) -> Any:
    if isinstance(value, str):
        return _render_ansible_strict(
            raw=value,
            var_name=field_name,
            variables=variables,
        )

    if isinstance(value, list):
        return [
            render_domain_value(item, variables, f"{field_name}[{idx}]")
            for idx, item in enumerate(value)
        ]

    if isinstance(value, dict):
        return {
            key: render_domain_value(item, variables, f"{field_name}.{key}")
            for key, item in value.items()
        }

    return value


def build_applications_from_roles(
    roles_dir: Path, domain_primary: str
) -> dict[str, dict[str, Any]]:
    variables = {"DOMAIN_PRIMARY": domain_primary}
    applications: dict[str, dict[str, Any]] = {}

    for role_dir in sorted(roles_dir.iterdir()):
        vars_main = role_dir / "vars" / "main.yml"
        config_main = role_dir / "config" / "main.yml"
        if not vars_main.exists() or not config_main.exists():
            continue

        vars_data = load_yaml_mapping(vars_main)
        application_id = vars_data.get("application_id")
        if not isinstance(application_id, str) or not application_id.strip():
            continue

        config_data = load_yaml_mapping(config_main)
        server = config_data.get("server")
        if not isinstance(server, dict):
            continue

        domains = server.get("domains")
        if not isinstance(domains, dict):
            continue

        applications[application_id] = {
            "server": {
                "domains": render_domain_value(
                    domains,
                    variables,
                    f"{application_id}.server.domains",
                )
            }
        }

    return applications


def list_derived_domains(domain_primary: str) -> list[str]:
    primary = str(domain_primary).strip().lower()
    if not primary:
        return []

    # Keep non-role domains that are part of the stack contract in one place.
    return [f"test.{primary}"]


def list_application_domains(roles_dir: Path, domain_primary: str) -> list[str]:
    applications = build_applications_from_roles(roles_dir, domain_primary)
    domains = set(_build_domain_index(applications).keys())
    domains.update(list_derived_domains(domain_primary))
    return sorted(domains)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List rendered canonical domains and aliases from role configs."
    )
    parser.add_argument(
        "--roles-dir",
        default=str(PROJECT_ROOT / "roles"),
        help="Path to the roles directory",
    )
    parser.add_argument(
        "--domain-primary",
        default=os.environ.get("DOMAIN", "infinito.example"),
        help="Value used for DOMAIN_PRIMARY rendering",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roles_dir = Path(args.roles_dir).resolve()
    if not roles_dir.is_dir():
        print(f"Roles directory not found: {roles_dir}", file=sys.stderr)
        return 1

    for domain in list_application_domains(roles_dir, args.domain_primary):
        print(domain)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
