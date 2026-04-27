"""In-process YAML loader with per-path memoisation.

Many CLI tools walk the same `roles/<role>/<config|vars|meta>/...yml`
files multiple times during a single invocation (dependency resolution,
service resolution, role introspection, ...). Each direct
`yaml.safe_load(path.read_text())` re-parses YAML and re-touches disk.

This module exposes a single cached `load_yaml(path)` so each absolute
path is parsed at most once per Python process. `dump_yaml` writes
through and evicts the cached entry. `invalidate(path)` is the explicit
escape hatch when a caller knows a file was changed externally.

CACHE SEMANTICS
- Cache key: `str(Path(path).resolve())`. Symlinks resolve once at the
  cache boundary so the same target shares an entry regardless of how
  callers spell the path.
- Cached value: the dict returned by `yaml.safe_load`. **The same dict
  instance is returned to every caller**, so callers that mutate the
  result MUST `copy.deepcopy()` it first. Treat the value as read-only.
- Lifetime: process-wide. The cache is intentionally NOT invalidated by
  external file changes; CLI tools are short-lived and the assumption
  "the on-disk file does not change while my process runs" holds.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

import yaml


_MISSING = object()
_CACHE: Dict[str, Any] = {}


def _key(path) -> str:
    return str(Path(path).resolve())


def _load_raw(path, *, default_if_missing: Any) -> Any:
    """Cached parse without root-shape validation.

    Returns whatever `yaml.safe_load` produces (dict, list, scalar,
    None coerced to `{}` for empty files). Callers wrap this with
    their own validation.
    """
    key = _key(path)
    if key in _CACHE:
        return _CACHE[key]

    p = Path(path)
    if not p.exists():
        if default_if_missing is _MISSING:
            raise FileNotFoundError(p)
        # Do NOT cache the synthetic default: a later `dump_yaml` may
        # create the file, and we want the next read to pick the real
        # content up. Caching the empty default here would mask that.
        return default_if_missing

    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        data = {}
    _CACHE[key] = data
    return data


def load_yaml(path, *, default_if_missing: Any = _MISSING) -> Dict[str, Any]:
    """Load a YAML file as a dict, memoised by absolute path.

    `default_if_missing` controls the missing-file behaviour:
    - Default (`_MISSING`): raise `FileNotFoundError` for callers that
      want to fail loud (resolution code).
    - Pass a value (typically `{}`): return that value when the file
      does not exist, mirroring the historical
      `cli.create.inventory.yaml_io.load_yaml` behaviour.

    Raises `ValueError` when the YAML root is not a mapping; use
    `load_yaml_any` for files whose root is a list or scalar.
    """
    data = _load_raw(path, default_if_missing=default_if_missing)
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected a YAML mapping at top-level in {path}, got {type(data).__name__}"
        )
    return data


def load_yaml_any(path, *, default_if_missing: Any = _MISSING) -> Any:
    """Memoised YAML load that accepts any root shape (dict, list,
    scalar). Use this for files where the root is not a mapping (e.g.
    Ansible task lists, the root list in `meta/variants.yml`).

    Empty files surface as `{}` (matching `yaml.safe_load(...) or {}`
    semantics that most call sites already rely on).
    """
    return _load_raw(path, default_if_missing=default_if_missing)


def dump_yaml(path, data: Mapping[str, Any]) -> None:
    """Write `data` to `path` as YAML and evict the cached entry.

    The next `load_yaml(path)` will parse the just-written file (and
    cache the result), which is what callers expect when a CLI tool
    edits a file mid-run.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(dict(data), f, sort_keys=False, default_flow_style=False)
    _CACHE.pop(_key(p), None)


def invalidate(path) -> None:
    """Drop one path from the cache.

    Use when the file was changed by code that does not go through
    `dump_yaml` (e.g. an external subprocess, a manual file rewrite,
    a fixture in tests).
    """
    _CACHE.pop(_key(path), None)


def _reset() -> None:
    """Test-only helper: clear the entire cache.

    Named ``_reset`` for parity with the per-domain reset helpers in
    sibling modules (``applications._reset``, ``users._reset``,
    ``domains._reset``, ``base._reset``); ``utils.cache._reset_cache_for_tests``
    orchestrates calls to all of them.
    """
    _CACHE.clear()


# Backwards-compatible alias for in-tree callers that may still reference
# the old name.
_reset_cache_for_tests = _reset
