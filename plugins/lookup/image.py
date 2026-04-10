from __future__ import annotations

from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase


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

    The lookup prefers images_overrides.<role>.<service> over local defaults
    from images.<service>, falling back field-wise when an override is absent.
    """

    def run(
        self,
        terms: List[Any],
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Any]:
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

        defaults = vars_.get("images", {}) or {}
        if not isinstance(defaults, dict):
            raise AnsibleError("image: Ansible variable 'images' must be a mapping")

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
    def _infer_role_id(vars_: Dict[str, Any]) -> str:
        role_name = _non_blank_string(vars_.get("role_name"))
        if role_name:
            return role_name

        raise AnsibleError(
            "image: could not infer role_id; set role_name or pass role_id explicitly"
        )

    @staticmethod
    def _merge_entry(
        *,
        role_id: str,
        service_name: str,
        defaults: Dict[str, Any],
        overrides_root: Dict[str, Any],
    ) -> Dict[str, str]:
        merged: Dict[str, str] = {}

        default_entry = defaults.get(service_name, {})
        if default_entry is not None and not isinstance(default_entry, dict):
            raise AnsibleError(
                f"image: images.{service_name} must be a mapping in role '{role_id}'"
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
