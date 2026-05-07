"""Single-pass project scanner for `lookup('config', ...)` calls.

Each `test_*.py` in this package consumes :func:`get_scan` to grab the
shared, lazily-built :class:`ScanResult`. Building the scan walks every
project file once and resolves application defaults / user defaults /
per-role schemas; caching it via ``functools.lru_cache`` keeps the
test-suite total well under the legacy single-class ``setUpClass`` cost
even though we now have one class per check.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from utils.annotations.suppress import is_suppressed_at
from utils.cache.applications import get_application_defaults
from utils.cache.files import iter_project_files_with_content
from utils.cache.users import get_user_defaults
from utils.cache.yaml import load_yaml_any


# Rule key consumed by every `tests/integration/lookups/config/test_*.py`.
# A marker in `same-or-above` position skips the call from all four
# scanners (literal / variable / wildcard / role-local). See
# docs/contributing/actions/testing/suppression.md.
SUPPRESS_RULE: str = "lookup-config-path"


PATTERN = re.compile(
    r"lookup\(\s*['\"]config['\"]\s*,\s*([^,]+?)\s*,\s*['\"]([^'\"]+)['\"]"
)
# Captures the entire `<path-expr>` of a `lookup('config', <app>, <expr>)`
# call up to the closing paren so we can rebuild the wildcard template
# from `~`-concatenations of literals and barewords.
CONCAT_PATTERN = re.compile(
    r"lookup\(\s*['\"]config['\"]\s*,\s*([^,]+?)\s*,\s*(.+?)\s*\)"
)


def role_id_from_path(file_path: Path) -> str | None:
    """Return the role id when ``file_path`` lives under ``roles/<role>/...``."""
    parts = file_path.parts
    try:
        idx = parts.index("roles")
    except ValueError:
        return None
    if idx + 1 >= len(parts):
        return None
    return parts[idx + 1]


def expr_to_wildcard_path(expr: str) -> str | None:
    """Convert a `~`-concatenated lookup-path expression into a dotted
    path with `*` placeholders for every Jinja variable segment.

    Examples:
      ``'services.' ~ entity_name ~ '.ports.inter'`` -> ``services.*.ports.inter``
      ``'services.openldap.ports.local.' ~ _ldap_protocol`` -> ``services.openldap.ports.local.*``

    Returns ``None`` when the expression cannot be parsed (mismatched
    quotes, unrecognised operators, etc.) so the caller can skip it.
    """
    parts: list[str] = []
    i = 0
    n = len(expr)
    expecting_value = True
    while i < n:
        ch = expr[i]
        if ch.isspace():
            i += 1
            continue
        if expecting_value:
            if ch in ("'", '"'):
                quote = ch
                j = expr.find(quote, i + 1)
                if j == -1:
                    return None
                parts.append(expr[i + 1 : j])
                i = j + 1
            else:
                j = i
                while j < n and not expr[j].isspace() and expr[j] != "~":
                    j += 1
                token = expr[i:j].strip()
                if not token:
                    return None
                parts.append("*")
                i = j
            expecting_value = False
        else:
            if ch == "~":
                expecting_value = True
                i += 1
            else:
                return None
    if expecting_value:
        return None
    raw = "".join(parts)
    segments = [seg for seg in raw.split(".") if seg != ""]
    return ".".join(segments) if segments else None


Occurrence = Tuple[Path, int]


@dataclass(frozen=True)
class ScanResult:
    root: Path
    application_defaults: Dict[str, Any]
    user_defaults: Dict[str, Any]
    role_schemas: Dict[str, Dict[str, Any]]
    role_for_app: Dict[str, str]
    literal_paths: Dict[str, Dict[str, List[Occurrence]]] = field(default_factory=dict)
    variable_paths: Dict[str, List[Occurrence]] = field(default_factory=dict)
    wildcard_paths: Dict[Tuple[str, str], List[Occurrence]] = field(default_factory=dict)
    role_local_paths: Dict[Tuple[str, str], List[Occurrence]] = field(
        default_factory=dict
    )


def _is_quoted(token: str) -> bool:
    return (token.startswith("'") and token.endswith("'")) or (
        token.startswith('"') and token.endswith('"')
    )


def _line_is_commented(text: str, match_start: int) -> bool:
    """Return True when the lookup match sits on a comment-only line or
    is preceded on the same line by a `#` inline comment marker."""
    start = text.rfind("\n", 0, match_start) + 1
    end = text.find("\n", start)
    line = text[start:end] if end != -1 else text[start:]
    if line.lstrip().startswith("#"):
        return True
    idx_call = line.find("lookup")
    idx_hash = line.find("#")
    return 0 <= idx_hash < idx_call


def _build_role_for_app_map(roles_root: Path) -> Dict[str, str]:
    """Walk ``roles/`` once and return ``{application_id: role_dir_name}``.

    Replaces the per-app ``plugins.filter.get_role.get_role`` call which is
    O(n) per lookup (it scans every role's vars/main.yml). Calling it once
    per application id makes role-schema preload O(n²); doing the walk
    once here keeps it O(n) and routes every YAML read through the
    process-wide ``utils.cache.yaml.load_yaml_any`` cache.
    """
    mapping: Dict[str, str] = {}
    if not roles_root.is_dir():
        return mapping
    for role_dir in roles_root.iterdir():
        if not role_dir.is_dir():
            continue
        vars_file = role_dir / "vars" / "main.yml"
        if not vars_file.is_file():
            continue
        data = load_yaml_any(vars_file, default_if_missing={}) or {}
        if not isinstance(data, dict):
            continue
        app_id = data.get("application_id")
        if isinstance(app_id, str):
            mapping[app_id] = role_dir.name
    return mapping


def _build_role_schemas(
    application_defaults: Dict[str, Any], roles_root: Path
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    role_schemas: Dict[str, Dict[str, Any]] = {}
    role_for_app = _build_role_for_app_map(roles_root)
    for app_id in application_defaults:
        role = role_for_app.get(app_id)
        if role is None:
            continue
        schema_file = roles_root / role / "meta" / "schema.yml"
        if not schema_file.is_file():
            continue
        schema = load_yaml_any(schema_file, default_if_missing={}) or {}
        if isinstance(schema, dict):
            role_schemas[app_id] = schema
    return role_schemas, role_for_app


def _scan_literal_match(
    result: ScanResult,
    file_path: Path,
    text: str,
    lines: List[str],
    match: re.Match[str],
) -> None:
    if _line_is_commented(text, match.start()):
        return
    lineno = text.count("\n", 0, match.start()) + 1
    if is_suppressed_at(lines, lineno, SUPPRESS_RULE, mode="same-or-above"):
        return
    app_arg = match.group(1).strip()
    path_arg = match.group(2).strip()
    if "{%" in path_arg:
        return
    if _is_quoted(app_arg):
        app_id = app_arg.strip("'\"")
        if path_arg.endswith("."):
            # Partial path — concatenated with a `~ var` suffix elsewhere.
            # Validated through variable_paths' wildcard-prefix branch.
            result.variable_paths.setdefault(path_arg, []).append((file_path, lineno))
        else:
            result.literal_paths.setdefault(app_id, {}).setdefault(
                path_arg, []
            ).append((file_path, lineno))
        return
    # Variable app argument (typically `application_id`).
    result.variable_paths.setdefault(path_arg, []).append((file_path, lineno))
    if not path_arg.endswith("."):
        role_id = role_id_from_path(file_path)
        if role_id is not None:
            result.role_local_paths.setdefault((role_id, path_arg), []).append(
                (file_path, lineno)
            )


def _scan_concat_match(
    result: ScanResult,
    file_path: Path,
    text: str,
    lines: List[str],
    match: re.Match[str],
) -> None:
    if _line_is_commented(text, match.start()):
        return
    app_arg = match.group(1).strip()
    expr = match.group(2).strip()
    if "~" not in expr or "{%" in expr:
        return
    wildcard_path = expr_to_wildcard_path(expr)
    if wildcard_path is None:
        return
    lineno = text.count("\n", 0, match.start()) + 1
    if is_suppressed_at(lines, lineno, SUPPRESS_RULE, mode="same-or-above"):
        return
    if _is_quoted(app_arg):
        role_id = app_arg.strip("'\"")
    else:
        role_id = role_id_from_path(file_path)
    if role_id is None:
        return
    result.wildcard_paths.setdefault((role_id, wildcard_path), []).append(
        (file_path, lineno)
    )


# Extensions that may legitimately host `lookup('config', ...)` calls in
# this project: Ansible YAML and Jinja templates. Restricting the walk
# this way skips the bulk of binary / icon / web-asset files entirely,
# which the underlying file-content cache otherwise has to read once.
_SCANNED_EXTENSIONS: Tuple[str, ...] = (".yml", ".yaml", ".j2")


@functools.lru_cache(maxsize=1)
def get_scan() -> ScanResult:
    """Return the cached project-wide scan of `lookup('config', ...)` calls.

    Performance notes
    -----------------
    The walk is bounded both by file extension (``_SCANNED_EXTENSIONS``)
    and by a literal substring pre-filter ("lookup"). The pre-filter is
    O(len(text)) and cuts out every file that cannot match either regex
    before we pay the full ``re.finditer`` cost.
    The underlying ``iter_project_files`` and ``read_text`` helpers are
    already process-cached (``functools.lru_cache``), so subsequent test
    classes in the same run hit the cache for free.
    """
    root = Path(__file__).resolve().parents[4]
    roles_root = root / "roles"
    application_defaults = get_application_defaults(roles_dir=roles_root)
    user_defaults = get_user_defaults(roles_dir=roles_root)
    role_schemas, role_for_app = _build_role_schemas(application_defaults, roles_root)

    result = ScanResult(
        root=root,
        application_defaults=application_defaults,
        user_defaults=user_defaults,
        role_schemas=role_schemas,
        role_for_app=role_for_app,
    )

    for path_str, text in iter_project_files_with_content(
        extensions=_SCANNED_EXTENSIONS,
        exclude_tests=True,
        exclude_dirs=("docs",),
    ):
        if "lookup" not in text:
            continue
        file_path = Path(path_str)
        # Split once per file so `is_suppressed_at` can index lines for
        # both regex passes without re-splitting.
        lines = text.splitlines()
        for m in PATTERN.finditer(text):
            _scan_literal_match(result, file_path, text, lines, m)
        for m in CONCAT_PATTERN.finditer(text):
            _scan_concat_match(result, file_path, text, lines, m)

    return result
