from __future__ import annotations

import copy
import glob
import os
from collections import OrderedDict
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

import yaml

from plugins.filter.merge_with_defaults import merge_with_defaults
from plugins.lookup.application_gid import LookupModule as ApplicationGidLookup
from utils.dict_renderer import DictRenderer
from utils.templating import _templar_render_best_effort

try:
    from ansible.parsing.vault import EncryptedString as _AnsibleEncryptedString
except Exception:
    _AnsibleEncryptedString = None


def _decrypt_ansible_encrypted_strings(value: Any) -> Any:
    """Recursively convert Ansible EncryptedString values to plaintext str.

    Ansible 2.19+ refuses to store EncryptedString as an intermediate variable
    during task arg finalization, so decrypt at the lookup boundary.
    """
    if _AnsibleEncryptedString is not None and isinstance(
        value, _AnsibleEncryptedString
    ):
        try:
            return str(value)
        except Exception:
            return value
    if isinstance(value, Mapping):
        return {k: _decrypt_ansible_encrypted_strings(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decrypt_ansible_encrypted_strings(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_decrypt_ansible_encrypted_strings(v) for v in value)
    return value


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROLES_DIR = PROJECT_ROOT / "roles"
DEFAULT_TOKENS_FILE = Path("/var/lib/infinito/secrets/tokens.yml")

_APPLICATIONS_DEFAULTS_CACHE: dict[str, dict[str, Any]] = {}
_USERS_DEFAULTS_CACHE: dict[str, dict[str, Any]] = {}


def _cache_key(roles_dir: Path) -> str:
    return str(roles_dir.resolve())


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, Mapping) and isinstance(override, Mapping):
        merged = {k: copy.deepcopy(v) for k, v in base.items()}
        for key, value in override.items():
            merged[key] = _deep_merge(merged.get(key), value)
        return merged
    return copy.deepcopy(override)


def _merge_users(
    defaults: Mapping[str, Any],
    overrides: Optional[Mapping[str, Any]],
) -> dict[str, Any]:
    merged = {key: copy.deepcopy(value) for key, value in defaults.items()}
    for key, value in (overrides or {}).items():
        merged[key] = _deep_merge(merged.get(key, {}), value)
    return merged


def _resolve_roles_dir(*, roles_dir: Optional[str | os.PathLike[str]] = None) -> Path:
    return Path(roles_dir).resolve() if roles_dir else ROLES_DIR.resolve()


def _compute_reserved_usernames(roles_dir: Path) -> list[str]:
    reserved: set[str] = set()
    for role_dir in roles_dir.iterdir():
        if not role_dir.is_dir():
            continue
        candidate = role_dir.name.rsplit("-", 1)[-1]
        if candidate.isalnum() and candidate.islower():
            reserved.add(candidate)
    return sorted(reserved)


def _load_user_defs(roles_dir: Path) -> OrderedDict[str, dict[str, Any]]:
    pattern = os.path.join(str(roles_dir), "*/users/main.yml")
    files = sorted(glob.glob(pattern))
    merged: OrderedDict[str, dict[str, Any]] = OrderedDict()

    for filepath in files:
        data = _load_yaml_mapping(Path(filepath))
        users = data.get("users", {})
        if not isinstance(users, dict):
            continue

        for key, overrides in users.items():
            if not isinstance(overrides, dict):
                raise ValueError(f"Invalid definition for user '{key}' in {filepath}")

            if key not in merged:
                merged[key] = copy.deepcopy(overrides)
                continue

            existing = merged[key]
            for field, value in overrides.items():
                if field in existing and existing[field] != value:
                    raise ValueError(
                        f"Conflict for user '{key}': field '{field}' has existing value "
                        f"'{existing[field]}', tried to set '{value}' in {filepath}"
                    )
            existing.update(copy.deepcopy(overrides))

    return merged


def _build_users(
    defs: OrderedDict[str, dict[str, Any]],
    primary_domain: str,
    start_id: int,
    become_pwd: str,
) -> OrderedDict[str, dict[str, Any]]:
    users: OrderedDict[str, dict[str, Any]] = OrderedDict()
    used_uids = set()

    for key, overrides in defs.items():
        if "uid" in overrides:
            uid = overrides["uid"]
            if uid in used_uids:
                raise ValueError(f"Duplicate uid {uid} for user '{key}'")
            used_uids.add(uid)

    next_uid = start_id

    def allocate_uid() -> int:
        nonlocal next_uid
        while next_uid in used_uids:
            next_uid += 1
        free_uid = next_uid
        used_uids.add(free_uid)
        next_uid += 1
        return free_uid

    for key, overrides in defs.items():
        username = overrides.get("username", key)
        firstname = overrides.get("firstname", f"{username}")
        lastname = overrides.get("lastname", f"{primary_domain}")
        email = overrides.get("email", f"{username}@{primary_domain}")
        description = overrides.get(
            "description", f"Created by Infinito.Nexus Ansible for {primary_domain}"
        )
        roles = overrides.get("roles", [])
        password = overrides.get("password", become_pwd)
        reserved = overrides.get("reserved", False)
        tokens = overrides.get("tokens", {})
        authorized_keys = overrides.get("authorized_keys", [])

        uid = overrides["uid"] if "uid" in overrides else allocate_uid()
        gid = overrides.get("gid", uid)

        users[key] = {
            "username": username,
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "password": password,
            "uid": uid,
            "gid": gid,
            "roles": roles,
            "tokens": tokens,
            "authorized_keys": authorized_keys,
            "reserved": reserved,
            "description": description,
        }

    seen_usernames: set[str] = set()
    seen_emails: set[str] = set()
    for key, entry in users.items():
        username = entry["username"]
        email = entry["email"]
        if username in seen_usernames:
            raise ValueError(f"Duplicate username '{username}' in merged users")
        if email in seen_emails:
            raise ValueError(f"Duplicate email '{email}' in merged users")
        seen_usernames.add(username)
        seen_emails.add(email)

    return users


def _load_store_users(file_tokens: Optional[str | os.PathLike[str]]) -> dict[str, Any]:
    if not file_tokens:
        return {}

    path = Path(file_tokens)
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}

    users = data.get("users", {})
    return users if isinstance(users, dict) else {}


def _resolve_tokens_file(variables: Optional[Mapping[str, Any]]) -> Path:
    candidates: list[Path] = []

    def _add_candidate(value: Any) -> None:
        if value is None:
            return
        text = str(value).strip()
        if text:
            candidates.append(Path(text))

    variables = variables or {}
    _add_candidate(variables.get("FILE_TOKENS"))

    dir_secrets = variables.get("DIR_SECRETS")
    if dir_secrets:
        _add_candidate(Path(str(dir_secrets)) / "tokens.yml")

    dir_var_lib = variables.get("DIR_VAR_LIB")
    if dir_var_lib:
        _add_candidate(Path(str(dir_var_lib)) / "secrets" / "tokens.yml")

    _add_candidate(os.environ.get("FILE_TOKENS"))

    env_dir_secrets = os.environ.get("DIR_SECRETS")
    if env_dir_secrets:
        _add_candidate(Path(env_dir_secrets) / "tokens.yml")

    env_dir_var_lib = os.environ.get("DIR_VAR_LIB")
    if env_dir_var_lib:
        _add_candidate(Path(env_dir_var_lib) / "secrets" / "tokens.yml")

    candidates.append(DEFAULT_TOKENS_FILE)

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            return candidate

    return candidates[0]


def _hydrate_users_tokens(
    users: Optional[Mapping[str, Any]],
    store_users: Optional[Mapping[str, Any]],
) -> dict[str, Any]:
    def _as_stripped(value: Any) -> Optional[str]:
        if value is None:
            return None
        return str(value).strip()

    def _is_effectively_empty(value: Any) -> bool:
        stripped = _as_stripped(value)
        return stripped is None or stripped == ""

    out: dict[str, Any] = copy.deepcopy(dict(users or {}))
    if not store_users:
        return out

    for user_key, user_data in store_users.items():
        if not isinstance(user_data, Mapping):
            continue
        store_tokens = user_data.get("tokens", {})
        if not isinstance(store_tokens, Mapping):
            continue

        out_user = copy.deepcopy(dict(out.get(user_key, {}) or {}))
        out_tokens = copy.deepcopy(dict(out_user.get("tokens", {}) or {}))

        for app_id, store_token in store_tokens.items():
            token = _as_stripped(store_token)
            if token is None or token == "":
                continue
            if _is_effectively_empty(out_tokens.get(app_id)):
                out_tokens[app_id] = token

        out_user["tokens"] = out_tokens
        out[user_key] = out_user

    return out


def _materialize_builtin_user_aliases(
    users: Optional[Mapping[str, Any]],
    variables: Optional[Mapping[str, Any]],
    templar: Any = None,
) -> dict[str, Any]:
    def _normalize_domain_candidate(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if ("{{" in text or "{%" in text) and variables:
            text = str(
                _templar_render_best_effort(templar, text, dict(variables))
            ).strip()
        if "://" in text:
            parsed = urlparse(text)
            text = parsed.hostname or text
        text = text.split("/", 1)[0].split(":", 1)[0].strip()
        return text

    def _to_primary_domain(value: Any) -> str:
        text = _normalize_domain_candidate(value)
        if not text:
            return ""
        labels = [label for label in text.split(".") if label]
        if len(labels) >= 2:
            return ".".join(labels[-2:])
        return text

    out: dict[str, Any] = copy.deepcopy(dict(users or {}))
    variables = variables or {}

    primary_domain = ""
    for candidate_key, extractor in (
        ("DOMAIN_PRIMARY", _normalize_domain_candidate),
        ("SYSTEM_EMAIL_DOMAIN", _normalize_domain_candidate),
        ("KEYCLOAK_DOMAIN", _to_primary_domain),
        ("domain", _to_primary_domain),
    ):
        primary_domain = extractor(variables.get(candidate_key))
        if primary_domain:
            break
    if not primary_domain:
        return out

    labels = [label for label in primary_domain.split(".") if label]
    alias_values = {
        "sld": labels[0] if labels else primary_domain,
        "tld": (labels[1] if len(labels) > 1 else (primary_domain + "_tld ")),
    }

    for alias_key, alias_value in alias_values.items():
        raw_user = out.get(alias_key)
        if not isinstance(raw_user, Mapping):
            continue

        raw_username = str(raw_user.get("username", ""))
        if "DOMAIN_PRIMARY.split" not in raw_username:
            continue

        updated_user = copy.deepcopy(dict(raw_user))
        updated_user["username"] = alias_value
        out[alias_key] = updated_user

    return out


def _resolve_override_mapping(
    variables: Optional[Mapping[str, Any]],
    key: str,
    templar: Any = None,
) -> dict[str, Any]:
    """Return runtime override mappings defensively.

    Nested `lookup('template', ...)` renders sometimes expose top-level lookup
    inputs like `applications`/`users` as non-mapping placeholder values instead
    of the original inventory overrides. Try to coerce via templar before
    falling back to aggregated defaults.
    """

    variables = variables or {}
    value = variables.get(key, {})
    if value is None:
        value = {}
    if not isinstance(value, Mapping) and templar is not None:
        try:
            rendered = templar.template(value, fail_on_undefined=False)
        except TypeError:
            try:
                rendered = templar.template(value)
            except Exception:
                rendered = value
        except Exception:
            rendered = value
        if isinstance(rendered, Mapping):
            value = rendered
    if not isinstance(value, Mapping):
        raw_key = {
            "applications": "_INFINITO_APPLICATIONS_RAW",
            "users": "_INFINITO_USERS_RAW",
        }.get(key)
        if raw_key:
            raw = variables.get(raw_key)
            if isinstance(raw, Mapping):
                value = raw
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _render_with_templar(
    value: Any,
    *,
    templar: Any,
    variables: Optional[dict[str, Any]],
    raw_applications: Optional[dict[str, Any]] = None,
    raw_users: Optional[dict[str, Any]] = None,
    max_rounds: int = 4,
) -> Any:
    if templar is None:
        return value

    base_variables = dict(variables or {})
    if raw_applications is not None:
        base_variables["_INFINITO_APPLICATIONS_RAW"] = raw_applications
    if raw_users is not None:
        base_variables["_INFINITO_USERS_RAW"] = raw_users

    def _render_scalar(raw: Any) -> Any:
        data = copy.deepcopy(raw)
        if isinstance(data, str):
            for _ in range(max_rounds):
                try:
                    rendered = _templar_render_best_effort(
                        templar, data, base_variables
                    )
                except Exception:
                    return data
                if rendered == data:
                    break
                data = rendered
            return data

        for _ in range(max_rounds):
            try:
                rendered = templar.template(data, fail_on_undefined=False)
            except TypeError:
                rendered = templar.template(data)
            except Exception:
                return data
            if rendered == data:
                break
            data = rendered
        return data

    def _render_deep(raw: Any) -> Any:
        if isinstance(raw, Mapping):
            return {key: _render_deep(item) for key, item in raw.items()}
        if isinstance(raw, list):
            return [_render_deep(item) for item in raw]
        if isinstance(raw, tuple):
            return tuple(_render_deep(item) for item in raw)
        return _render_scalar(raw)

    previous_available = getattr(templar, "available_variables", None)

    try:
        if hasattr(templar, "available_variables"):
            templar.available_variables = base_variables
        data = _render_deep(value)
    finally:
        if hasattr(templar, "available_variables"):
            templar.available_variables = previous_available

    return _decrypt_ansible_encrypted_strings(data)


def _build_application_defaults(roles_dir: Path) -> dict[str, Any]:
    gid_lookup = ApplicationGidLookup()
    applications: dict[str, Any] = {}

    for config_file in sorted(roles_dir.glob("*/config/main.yml")):
        role_dir = config_file.parents[1]
        application_id = role_dir.name
        config_data = _load_yaml_mapping(config_file)

        if config_data:
            group_id = gid_lookup.run([application_id], roles_dir=str(roles_dir))[0]
            config_data["group_id"] = group_id

            users_meta = _load_yaml_mapping(role_dir / "users" / "main.yml")
            users_data = users_meta.get("users", {})
            if isinstance(users_data, dict) and users_data:
                config_data["users"] = {
                    user_key: "{{ lookup('users', " + repr(user_key) + ") }}"
                    for user_key in users_data
                }

        applications[application_id] = config_data

    rendered = DictRenderer().render({"applications": applications})
    apps = rendered.get("applications", {})
    if not isinstance(apps, dict):
        raise ValueError("Rendered applications payload must be a mapping")
    return {key: apps[key] for key in sorted(apps)}


def get_application_defaults(
    *, roles_dir: Optional[str | os.PathLike[str]] = None
) -> dict[str, Any]:
    resolved_roles_dir = _resolve_roles_dir(roles_dir=roles_dir)
    key = _cache_key(resolved_roles_dir)
    cached = _APPLICATIONS_DEFAULTS_CACHE.get(key)
    if cached is None:
        cached = _build_application_defaults(resolved_roles_dir)
        _APPLICATIONS_DEFAULTS_CACHE[key] = cached
    return copy.deepcopy(cached)


def get_user_defaults(
    *, roles_dir: Optional[str | os.PathLike[str]] = None
) -> dict[str, Any]:
    resolved_roles_dir = _resolve_roles_dir(roles_dir=roles_dir)
    key = _cache_key(resolved_roles_dir)
    cached = _USERS_DEFAULTS_CACHE.get(key)
    if cached is None:
        definitions = _load_user_defs(resolved_roles_dir)
        for reserved_username in _compute_reserved_usernames(resolved_roles_dir):
            if reserved_username not in definitions:
                definitions[reserved_username] = {"reserved": True}
        built = _build_users(
            definitions,
            primary_domain="{{ SYSTEM_EMAIL_DOMAIN }}",
            start_id=1001,
            become_pwd="{{ 42 | strong_password }}",
        )
        cached = {key: built[key] for key in sorted(built)}
        _USERS_DEFAULTS_CACHE[key] = cached
    return copy.deepcopy(cached)


def get_merged_applications(
    *,
    variables: Optional[dict[str, Any]] = None,
    roles_dir: Optional[str | os.PathLike[str]] = None,
    templar: Any = None,
) -> dict[str, Any]:
    variables = variables or {}
    defaults = get_application_defaults(roles_dir=roles_dir)
    overrides = _resolve_override_mapping(variables, "applications", templar=templar)

    merged = merge_with_defaults(defaults, overrides)
    raw_users = get_merged_users(
        variables=variables,
        roles_dir=roles_dir,
        templar=None,
    )
    return _render_with_templar(
        merged,
        templar=templar,
        variables=variables,
        raw_applications=merged,
        raw_users=raw_users,
    )


def get_merged_users(
    *,
    variables: Optional[dict[str, Any]] = None,
    roles_dir: Optional[str | os.PathLike[str]] = None,
    templar: Any = None,
) -> dict[str, Any]:
    variables = dict(variables or {})
    if not variables.get("DOMAIN_PRIMARY") and variables.get("SYSTEM_EMAIL_DOMAIN"):
        variables["DOMAIN_PRIMARY"] = variables["SYSTEM_EMAIL_DOMAIN"]
    defaults = get_user_defaults(roles_dir=roles_dir)
    overrides = _resolve_override_mapping(variables, "users", templar=templar)

    merged = _merge_users(defaults, overrides)
    hydrated = _hydrate_users_tokens(
        merged,
        _load_store_users(_resolve_tokens_file(variables)),
    )
    materialized = _materialize_builtin_user_aliases(
        hydrated,
        variables,
        templar=templar,
    )
    return _render_with_templar(
        materialized,
        templar=templar,
        variables=variables,
        raw_users=materialized,
    )


def _reset_cache_for_tests() -> None:
    _APPLICATIONS_DEFAULTS_CACHE.clear()
    _USERS_DEFAULTS_CACHE.clear()
