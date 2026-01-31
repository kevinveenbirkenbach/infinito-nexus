# module_utils/templating.py
from __future__ import annotations

import os
import re
from typing import Any, Optional

from ansible.errors import AnsibleError

# Match the "lookup('env','NAME')" head (without caring about trailing filters)
_RE_LOOKUP_ENV_HEAD = re.compile(
    r"""^lookup\(\s*['"]env['"]\s*,\s*['"]([^'"]+)['"]\s*\)\s*""",
    re.IGNORECASE,
)

_RE_ANY_LOOKUP = re.compile(r"""\blookup\s*\(""", re.IGNORECASE)

_RE_VARPATH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*$")
_RE_JINJA_BLOCK = re.compile(r"\{\{\s*(.*?)\s*\}\}", re.DOTALL)


def _get_by_path(variables: dict, path: str) -> Any:
    cur: Any = variables
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(path)
        cur = cur[part]
    return cur


def _apply_filter(value: Any, filt: str) -> Any:
    f = filt.strip()

    if f == "lower":
        return str(value).lower()

    if f == "upper":
        return str(value).upper()

    # default('x', true) -> treat None/"" as default
    if f.startswith("default(") and f.endswith(")"):
        inner = f[len("default(") : -1].strip()

        default_val: Any = ""
        if inner.startswith(("'", '"')):
            q = inner[0]
            end = inner.find(q, 1)
            default_val = inner[1:end] if end != -1 else ""
        else:
            default_val = inner.split(",", 1)[0].strip()

        if value is None:
            return default_val
        if str(value) == "":
            return default_val
        return value

    # Unknown filter -> no-op
    return value


def _fallback_eval_expr(expr: str, variables: dict) -> str:
    """
    Evaluate a single Jinja expression (no surrounding {{ }}).

    Supported subset (SAFE fallback only):
      - lookup('env','NAME')
      - VAR / VAR.path
      - filters: | lower, | upper, | default('x', true)

    Any other lookup(...) must NOT be handled here.
    """
    parts = [p.strip() for p in expr.split("|")]
    head = parts[0].strip()

    m = _RE_LOOKUP_ENV_HEAD.match(head)
    if m:
        key = m.group(1)
        val: Any = os.environ.get(key)
    else:
        if not _RE_VARPATH.match(head):
            raise ValueError(f"unsupported expression: {head}")
        try:
            val = _get_by_path(variables, head)
        except KeyError:
            val = None

    for filt in parts[1:]:
        val = _apply_filter(val, filt)

    return "" if val is None else str(val)


def _fallback_render_embedded(s: str, variables: dict) -> str:
    def repl(m: re.Match) -> str:
        expr = (m.group(1) or "").strip()
        return _fallback_eval_expr(expr, variables)

    return _RE_JINJA_BLOCK.sub(repl, s)


def _contains_non_env_lookup(s: str) -> bool:
    """
    True if any embedded {{ ... }} contains lookup(...) that is NOT lookup('env', ...).

    IMPORTANT:
    - Allow lookup('env', ...) even when followed by filters, e.g.
      {{ lookup('env','domain') | default('x', true) }}
    """
    for m in _RE_JINJA_BLOCK.finditer(s):
        expr = (m.group(1) or "").strip()
        if _RE_ANY_LOOKUP.search(expr):
            # If the expression starts with lookup('env', ...) (filters allowed), it's safe
            if _RE_LOOKUP_ENV_HEAD.match(expr):
                continue
            return True
    return False


def _set_templar_var(templar: Any, name: str, value: Any) -> tuple[bool, Any]:
    """
    Best-effort setter for templar flags across Ansible versions.
    Returns (changed, previous_value).
    """
    if templar is None or not hasattr(templar, name):
        return False, None
    try:
        prev = getattr(templar, name)
        setattr(templar, name, value)
        return True, prev
    except Exception:
        return False, None


def _templar_render_best_effort(templar: Any, s: str, variables: dict) -> str:
    """
    Render with Ansible templar across versions.

    Policy:
    - Always try templar first (so ALL lookup(...) can be evaluated properly).
    - If templar returns unchanged while Jinja exists:
        - If string contains non-env lookup(...): DO NOT fallback (leave as-is)
        - Else: fallback is allowed (env + varpaths + simple filters)
    """
    if templar is None:
        return _fallback_render_embedded(s, variables)

    prev_avail: Optional[Any] = None
    avail_changed = False

    # Temporarily force lookups ON (different Ansible versions use different flags)
    disable_changed_1, prev_disable_1 = _set_templar_var(
        templar, "disable_lookups", False
    )
    disable_changed_2, prev_disable_2 = _set_templar_var(
        templar, "_disable_lookups", False
    )

    if hasattr(templar, "available_variables"):
        try:
            prev_avail = templar.available_variables
            templar.available_variables = variables
            avail_changed = True
        except Exception:
            prev_avail = None
            avail_changed = False

    try:
        try:
            out = templar.template(s, fail_on_undefined=True)
        except TypeError:
            out = templar.template(s)
    finally:
        if (
            avail_changed
            and prev_avail is not None
            and hasattr(templar, "available_variables")
        ):
            try:
                templar.available_variables = prev_avail
            except Exception:
                pass

        if disable_changed_2:
            try:
                setattr(templar, "_disable_lookups", prev_disable_2)
            except Exception:
                pass
        if disable_changed_1:
            try:
                setattr(templar, "disable_lookups", prev_disable_1)
            except Exception:
                pass

    out_s = "" if out is None else str(out)

    # If templar didn't change anything while Jinja exists:
    if out_s.strip() == s.strip() and ("{{" in s or "{%" in s):
        # If it contains any non-env lookup(...), fallback would be wrong.
        if _contains_non_env_lookup(s):
            return out_s

        # Otherwise safe to attempt limited fallback for embedded patterns.
        return _fallback_render_embedded(s, variables)

    return out_s


def render_ansible_strict(
    *,
    templar: Any,
    raw: Any,
    var_name: str,
    err_prefix: str,
    variables: dict,
    max_rounds: int = 6,
) -> str:
    """
    Strict rendering helper for lookup/filter plugins.

    - Renders via Ansible templar when possible (lookup(), filters, vars).
    - Automatic fallback is enabled for a SAFE subset (env lookup + varpaths + simple filters)
      only when templar can't/won't render and NO non-env lookup(...) is present.
    - Re-renders multiple rounds because intermediate results can still contain Jinja.
    - Hard-fails if output is empty or still contains unresolved Jinja markers.
    """
    if raw is None:
        raise AnsibleError(f"{err_prefix}: {var_name} resolved to None")

    s = str(raw)

    out = s
    for _ in range(max_rounds):
        if ("{{" not in out) and ("{%" not in out):
            break
        out2 = _templar_render_best_effort(templar, out, variables)
        if out2 == out:
            break
        out = out2

    out = "" if out is None else str(out).strip()
    if not out:
        raise AnsibleError(
            f"{err_prefix}: {var_name} rendered to empty string. Raw: {s}"
        )

    if ("{{" in out) or ("{%" in out):
        raise AnsibleError(
            f"{err_prefix}: {var_name} still contains unresolved Jinja. Rendered: {out}. Raw: {s}"
        )

    return out
