from __future__ import annotations

from pathlib import Path
from typing import Any

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from utils.cache.yaml import load_yaml_any
from utils.roles import PROJECT_ROOT
from utils.roles.mapping import ROLE_FILE_META_SERVICES

_VALID_WANTS = frozenset({"all", "image", "version", "ref"})


def _non_blank_string(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


class LookupModule(LookupBase):
    """
    Resolve role-local image declarations with optional inventory overrides.

    Supported forms:
      - lookup('image', service_name[, want])
      - lookup('image', role_id, service_name[, want])

    Defaults are sourced from ``roles/<role_id>/meta/services.yml`` under
    the matching ``<service_name>`` entry's ``image`` and ``version``
    fields. Inventory overrides at
    ``images_overrides.<role_id>.<service_name>`` win field-wise over the
    role default.
    """

    def run(
        self,
        terms: list[Any],
        variables: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        terms = terms or []
        if len(terms) not in (1, 2, 3):
            raise AnsibleError(
                "image: requires service_name[, want] or role_id, service_name[, want]"
            )

        vars_ = (
            variables if variables is not None else self._templar.available_variables
        )

        if len(terms) == 1:
            role_id = self._infer_role_id(vars_)
            service_name = _non_blank_string(terms[0])
            want = "all"
        elif len(terms) == 2:
            inferred_want = _non_blank_string(terms[1]).lower()
            if inferred_want in _VALID_WANTS:
                role_id = self._infer_role_id(vars_)
                service_name = _non_blank_string(terms[0])
                want = inferred_want
            else:
                role_id = _non_blank_string(terms[0])
                service_name = _non_blank_string(terms[1])
                want = "all"
        else:
            role_id = _non_blank_string(terms[0])
            service_name = _non_blank_string(terms[1])
            want = _non_blank_string(terms[2]).lower() or "all"

        if not role_id:
            raise AnsibleError("image: role_id must not be empty")
        if not service_name:
            raise AnsibleError("image: service_name must not be empty")
        if want not in _VALID_WANTS:
            raise AnsibleError("image: want must be one of all, image, version, ref")

        defaults = self._load_role_services(role_id)

        overrides_root = vars_.get("images_overrides", {}) or {}
        if not isinstance(overrides_root, dict):
            raise AnsibleError(
                "image: Ansible variable 'images_overrides' must be a mapping"
            )

        merged = self._merge_entry(
            role_id=role_id,
            service_name=service_name,
            defaults=defaults,
            overrides_root=overrides_root,
        )

        if want == "all":
            return [merged]

        if want == "ref":
            image = _non_blank_string(merged.get("image"))
            version = _non_blank_string(merged.get("version"))
            if not image or not version:
                raise AnsibleError(
                    f"image: '{role_id}.{service_name}' is missing image or version for ref"
                )
            return [f"{image}:{version}"]

        value = _non_blank_string(merged.get(want))
        if not value:
            raise AnsibleError(
                f"image: '{role_id}.{service_name}' is missing required field '{want}'"
            )
        return [value]

    @staticmethod
    def _infer_role_id(vars_: dict[str, Any]) -> str:
        role_name = _non_blank_string(vars_.get("role_name"))
        if role_name:
            return role_name

        raise AnsibleError(
            "image: could not infer role_id; set role_name or pass role_id explicitly"
        )

    @staticmethod
    def _load_role_services(role_id: str) -> dict[str, Any]:
        services_path = Path(PROJECT_ROOT) / "roles" / role_id / ROLE_FILE_META_SERVICES
        if not services_path.is_file():
            raise AnsibleError(f"image: missing {services_path} for role '{role_id}'")
        loaded = load_yaml_any(str(services_path), default_if_missing={}) or {}
        if not isinstance(loaded, dict):
            raise AnsibleError(
                f"image: {services_path} must be a YAML mapping at the file root"
            )
        return loaded

    @staticmethod
    def _merge_entry(
        *,
        role_id: str,
        service_name: str,
        defaults: dict[str, Any],
        overrides_root: dict[str, Any],
    ) -> dict[str, str]:
        merged: dict[str, str] = {}

        default_entry = defaults.get(service_name, {})
        if default_entry is not None and not isinstance(default_entry, dict):
            raise AnsibleError(
                f"image: meta/services.yml entry '{service_name}' must be a mapping in role '{role_id}'"
            )
        if isinstance(default_entry, dict):
            for key in ("image", "version"):
                value = _non_blank_string(default_entry.get(key))
                if value:
                    merged[key] = value

        role_overrides = overrides_root.get(role_id, {})
        if role_overrides is not None and not isinstance(role_overrides, dict):
            raise AnsibleError(f"image: images_overrides.{role_id} must be a mapping")

        override_entry = role_overrides.get(service_name, {}) if role_overrides else {}
        if override_entry is not None and not isinstance(override_entry, dict):
            raise AnsibleError(
                f"image: images_overrides.{role_id}.{service_name} must be a mapping"
            )
        if isinstance(override_entry, dict):
            for key in ("image", "version"):
                value = _non_blank_string(override_entry.get(key))
                if value:
                    merged[key] = value

        if not merged:
            raise AnsibleError(
                f"image: no image mapping found for role '{role_id}' service '{service_name}'"
            )

        return merged
