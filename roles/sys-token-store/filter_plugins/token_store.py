# -*- coding: utf-8 -*-
"""
Ansible filter plugin: token store hydration helpers.

Rules:
- Preferred source is runtime users.*.tokens.* BUT only if non-empty after strip().
- Otherwise, token-store values are used.
- None / '' / whitespace-only values are treated as empty.
"""

from typing import Any, Dict, Mapping, Optional


def _as_stripped(value: Any) -> Optional[str]:
    """Return stripped string or None if value is None."""
    if value is None:
        return None
    return str(value).strip()


def _is_effectively_empty(value: Any) -> bool:
    """True if value is None or becomes '' after strip()."""
    s = _as_stripped(value)
    return s is None or s == ""


def hydrate_users_tokens(
    users: Optional[Mapping[str, Any]],
    store_users: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """
    Merge token store data into runtime users dict.

    - For each token in store_users[user]['tokens'][app] (non-empty):
      set users[user]['tokens'][app] if missing or empty in users.
    - users value wins only if it is non-empty after strip().
    """
    # Start with a shallow copy of users into a mutable dict.
    out: Dict[str, Any] = dict(users or {})

    if not store_users:
        return out

    for user_key, user_data in (store_users or {}).items():
        if not isinstance(user_data, Mapping):
            continue

        store_tokens = user_data.get("tokens", {})
        if not isinstance(store_tokens, Mapping):
            continue

        # Ensure user in output.
        out_user = dict(out.get(user_key, {}) or {})
        out_tokens = dict(out_user.get("tokens", {}) or {})

        for app_id, store_token in store_tokens.items():
            # Only consider meaningful store tokens
            store_token_str = _as_stripped(store_token)
            if store_token_str is None or store_token_str == "":
                continue

            existing = out_tokens.get(app_id, None)
            if _is_effectively_empty(existing):
                out_tokens[app_id] = store_token_str

        out_user["tokens"] = out_tokens
        out[user_key] = out_user

    return out


class FilterModule(object):
    def filters(self) -> Dict[str, Any]:
        return {
            "hydrate_users_tokens": hydrate_users_tokens,
        }
