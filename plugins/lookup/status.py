from __future__ import annotations

from typing import Any

from ansible.plugins.lookup import LookupBase

from utils.roles.validation.invokable import list_invokable_app_ids

_STATUS_CACHE: dict[tuple, dict[str, list[str]]] = {}


def _reset_cache_for_tests() -> None:
    _STATUS_CACHE.clear()


class LookupModule(LookupBase):
    def run(
        self,
        terms: list[Any],
        variables: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, list[str]]]:
        vars_ = variables or getattr(self._templar, "available_variables", {}) or {}

        whitelist = list(vars_.get("APPLICATIONS_WHITELIST") or [])
        groups = list(vars_.get("group_names") or [])
        key = (tuple(whitelist), tuple(groups))

        cached = _STATUS_CACHE.get(key)
        if cached is not None:
            return [cached]

        running = whitelist or groups
        result = {
            "whitelist": whitelist,
            "running": list(running),
            "groups": groups,
            "all": list(list_invokable_app_ids()),
        }
        _STATUS_CACHE[key] = result
        return [result]
