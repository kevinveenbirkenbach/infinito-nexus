"""Lint that every key declared in `roles/*/templates/playwright.env.j2`
is actually consumed by at least one Playwright JS file.

Two failure modes are collected and reported as one aggregated list:

* A role ships ``templates/playwright.env.j2`` but no
  ``files/playwright.spec.js`` next to it. The env file would render
  variables that nothing in the role's spec can read — likely a
  half-finished port.
* A specific ``KEY=`` declaration in the env file is never referenced
  via ``process.env.KEY`` (or ``process.env["KEY"]`` /
  ``process.env['KEY']``) by any JS file under the role's ``files/``
  tree or by the shared helpers in
  ``roles/test-e2e-playwright/files/*.js`` (e.g. ``service-gating.js``
  consumes the ``<X>_SERVICE_ENABLED`` flags). The shared dir is
  scanned so per-role specs that delegate gating to the helper still
  count their flags as used.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Iterable, List

from utils.cache.files import read_text


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise AssertionError("Repository root not found from test path.")


_KEY_LHS_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*=")

# Keys whose suffix marks them as dynamically consumed by a shared
# helper that reads `process.env` by computed key — they cannot be
# matched with a literal `process.env.<KEY>` regex. The
# ``_SERVICE_ENABLED`` family is read by
# `roles/test-e2e-playwright/files/service-gating.js` via
# ``Object.keys(process.env)`` plus a suffix-strip; declaring such a
# flag in `playwright.env.j2` is the contract that registers the
# service with the helper.
_DYNAMIC_KEY_SUFFIXES: tuple[str, ...] = ("_SERVICE_ENABLED",)

# Keys read by the Node.js runtime itself (not by user code), so a
# missing `process.env` reference is expected and not a bug.
_RUNTIME_KEYS: frozenset[str] = frozenset({"NODE_TLS_REJECT_UNAUTHORIZED"})


def _is_implicitly_consumed(key: str) -> bool:
    if key in _RUNTIME_KEYS:
        return True
    return any(key.endswith(suffix) for suffix in _DYNAMIC_KEY_SUFFIXES)


def _extract_env_keys(env_text: str) -> List[str]:
    """Return the ordered list of `KEY=` declarations in a
    `playwright.env.j2` body.

    Skips:
    * blank lines and ``#`` comments,
    * Jinja control / comment lines (``{% ... %}`` / ``{# ... #}``).
    A line that begins with a Jinja expression like ``{{ … }}`` is
    not a declaration and gets ignored as well.
    """
    keys: List[str] = []
    for line in env_text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("{%") or stripped.startswith("{#"):
            continue
        m = _KEY_LHS_RE.match(stripped)
        if m:
            keys.append(m.group(1))
    return keys


def _key_referenced(key: str, sources: Iterable[str]) -> bool:
    """Return True iff *key* appears as ``process.env.<KEY>`` or
    ``process.env["<KEY>"]`` / ``process.env['<KEY>']`` in any source."""
    pattern = re.compile(
        r"process\.env\.(?:"
        + re.escape(key)
        + r"\b|\[\s*['\"]"
        + re.escape(key)
        + r"['\"]\s*\])"
    )
    return any(pattern.search(text) for text in sources)


def _read_js_sources(directory: Path) -> List[str]:
    return [read_text(str(p)) for p in sorted(directory.rglob("*.js"))]


class TestPlaywrightEnvKeysUsed(unittest.TestCase):
    def test_env_keys_referenced_in_specs(self):
        root = _repo_root()
        roles_dir = root / "roles"
        shared_helpers_dir = roles_dir / "test-e2e-playwright" / "files"
        shared_sources: List[str] = (
            _read_js_sources(shared_helpers_dir) if shared_helpers_dir.is_dir() else []
        )

        missing_specs: List[str] = []
        unreferenced_keys: List[str] = []

        for env_path in sorted(roles_dir.glob("*/templates/playwright.env.j2")):
            # nocheck: project-root-import  walking from a discovered glob match (<role>/templates/...) up to its role dir, not the repo root
            role_dir = env_path.parents[1]
            role_name = role_dir.name
            spec_path = role_dir / "files" / "playwright.spec.js"
            env_rel = env_path.relative_to(root).as_posix()
            spec_rel = spec_path.relative_to(root).as_posix()

            if not spec_path.is_file():
                missing_specs.append(
                    f"{role_name}: {env_rel} exists but {spec_rel} is missing"
                )
                continue

            keys = _extract_env_keys(read_text(str(env_path)))
            if not keys:
                continue

            role_files_dir = role_dir / "files"
            role_sources = (
                _read_js_sources(role_files_dir) if role_files_dir.is_dir() else []
            )
            sources = role_sources + shared_sources

            for key in keys:
                if _is_implicitly_consumed(key):
                    continue
                if not _key_referenced(key, sources):
                    unreferenced_keys.append(
                        f"{role_name}: env key '{key}' from {env_rel} "
                        f"is never read via process.env in any .js under "
                        f"{role_dir.relative_to(root).as_posix()}/files/ "
                        f"or roles/test-e2e-playwright/files/"
                    )

        report: List[str] = []
        if missing_specs:
            report.append(
                f"{len(missing_specs)} role(s) ship a playwright.env.j2 without "
                f"a sibling playwright.spec.js:"
            )
            report.extend(f"- {m}" for m in missing_specs)
        if unreferenced_keys:
            report.append(
                f"{len(unreferenced_keys)} env key(s) declared but not consumed:"
            )
            report.extend(f"- {k}" for k in unreferenced_keys)
        if report:
            self.fail("\n".join(report))


if __name__ == "__main__":
    unittest.main()
