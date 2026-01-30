# module_utils/templating.py
from __future__ import annotations

import os
import re
from typing import Any

from ansible.errors import AnsibleError


_RE_LOOKUP_ENV = re.compile(
    r"""^lookup\(\s*['"]env['"]\s*,\s*['"]([^'"]+)['"]\s*\)\s*$"""
)
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

    # default('x', true)  -> treat None/"" as default
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

    Supported:
      - lookup('env','NAME')
      - VAR / VAR.path
      - filters: | lower, | upper, | default('x', true)

    This is a fallback when Ansible templar can't or won't evaluate.
    """
    parts = [p.strip() for p in expr.split("|")]
    head = parts[0]

    m = _RE_LOOKUP_ENV.match(head)
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


def _templar_render_best_effort(templar: Any, s: str, variables: dict) -> str:
    """
    Render with Ansible templar across versions.

    Compatibility:
    - Do NOT pass variables=... to templar.template() (breaks on some versions)
    - Instead set templar.available_variables temporarily.
    """
    if templar is None:
        return _fallback_render_embedded(s, variables)

    prev = None
    if hasattr(templar, "available_variables"):
        try:
            prev = templar.available_variables
            templar.available_variables = variables
        except Exception:
            prev = None

    try:
        try:
            out = templar.template(s, fail_on_undefined=True)
        except TypeError:
            out = templar.template(s)
    finally:
        if prev is not None and hasattr(templar, "available_variables"):
            try:
                templar.available_variables = prev
            except Exception:
                pass

    out_s = "" if out is None else str(out)

    # If templar didn't change anything while Jinja exists, fallback for embedded patterns.
    if out_s.strip() == s.strip() and ("{{" in s or "{%" in s):
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
    - If templar can't/won't render, applies safe fallback for embedded {{ ... }}.
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
