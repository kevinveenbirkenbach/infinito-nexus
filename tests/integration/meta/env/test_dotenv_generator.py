"""Drift + smoke guards for the project env generator.

The generator at ``cli/meta/env/__main__.py`` is the single source of
truth that materialises ``.env`` from the committed ``env/static.env``
at the repo root plus runtime context. This integration test locks in
two invariants:

1. **Drift**: every key declared in ``env/static.env`` is read by a
   handler in :mod:`utils.env.handlers` (exposed via
   ``PASSTHROUGH_STATIC_KEYS`` / ``GHA_STATIC_KEYS``). No silent drops.
   This is a cross-file consistency check, not a single-file lint.
2. **Smoke**: running ``python -m cli.meta.env`` end-to-end with a
   clean environment writes a ``.env`` containing the expected
   baseline of variables. Subprocess-driven, end-to-end -- hence
   integration, not unit / lint.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from typing import TYPE_CHECKING

from utils.cache.files import read_text
from utils.env.handlers import GHA_STATIC_KEYS, PASSTHROUGH_STATIC_KEYS

from . import PROJECT_ROOT

if TYPE_CHECKING:
    from pathlib import Path

STATIC_ENV = PROJECT_ROOT / "env" / "static.env"

# Baseline keys the rest of the codebase relies on after a clean
# (non-GHA, non-act) generation.
EXPECTED_BASELINE_KEYS = frozenset(
    {
        "INFINITO_SRC_DIR",
        "INFINITO_BIND_IP",
        "INFINITO_SUBNET",
        "INFINITO_GATEWAY",
        "INFINITO_DISTRO",
        "INFINITO_CONTAINER",
        "INFINITO_CONTAINER_NO_CA",
        "INFINITO_RUNNING_ON_ACT",
        "INFINITO_RUNNING_ON_GITHUB",
        "INFINITO_IS_WSL2",
        "INFINITO_COMPILE",
        "INFINITO_COMPILE_SILENCE",
        "INFINITO_PULL_POLICY",
        "INFINITO_MEM_LIMIT",
        "INFINITO_MEMSWAP_LIMIT",
        "INFINITO_CPUS",
        "INFINITO_WAIT_HEALTH_TIMEOUT_S",
        "INFINITO_DOCKER_VOLUME",
        "INFINITO_DOCKER_MOUNT",
        "INFINITO_OUTER_NETWORK_MTU",
        "INFINITO_TEST_DEPLOY_TYPE",
        "INFINITO_TEST_PATTERN",
        "INFINITO_TEST_RUNNER",
        "INFINITO_LINT_RUNNER",
        "INFINITO_DISTROS",
        "INFINITO_APPS",
        "INFINITO_SERVICES_DISABLED",
        "INFINITO_CMD",
        "INFINITO_DEBUG",
        "INFINITO_WHITELIST",
        "INFINITO_LIMIT_HOST",
        "INFINITO_BUNDLES",
        "INFINITO_FULL_CYCLE",
        "INFINITO_VARIANT",
        "INFINITO_RUN_FLAGS",
        "INFINITO_PARALLEL",
        "VENV",
        "INFINITO_VENV_BASE",
        "INFINITO_VENV_NAME",
        "INFINITO_VENV_FALLBACK",
        "PYTHON",
        "PIP",
        "PYTHONPATH",
        "INVENTORY_VARS_FILE",
        "INFINITO_REGISTRY_CACHE_HOST_PATH",
        "INFINITO_REGISTRY_CACHE_CA_HOST_PATH",
        "INFINITO_REGISTRY_CACHE_MAX_SIZE",
        "INFINITO_PACKAGE_CACHE_HOST_PATH",
        "INFINITO_PACKAGE_CACHE_PORT",
        "INFINITO_PACKAGE_CACHE_HEAP",
        "INFINITO_PACKAGE_CACHE_DIRECT_MEM",
        "INFINITO_PACKAGE_CACHE_BLOBSTORE_MAX",
        "INFINITO_PACKAGE_CACHE_ADMIN_PASSWORD",
        "INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR",
        "INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR",
        "INFINITO_PACKAGE_CACHE_FRONTEND_IP",
        "INFINITO_PACKAGE_CACHE_FRONTEND_INIT_IMAGE",
        "INFINITO_PACKAGE_CACHE_MAX_AGE_MIN",
        "INFINITO_IMAGE_TAG",
    }
)

# Same env/static.env parser as the generator (kept here to avoid importing
# the generator module just for the helper).
_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def parse_static_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in read_text(str(path)).splitlines():
        stripped = raw.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _LINE_RE.match(stripped)
        if not match:
            continue
        key, value = match.group(1), match.group(2)
        if value and value[0] not in ('"', "'"):
            value = value.split("#", 1)[0].rstrip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


def parse_dotenv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in read_text(str(path)).splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


def generator_referenced_keys() -> set[str]:
    """Return the set of env/static.env keys the generator actually reads.

    Sourced from the handler registry's ``PASSTHROUGH_STATIC_KEYS`` and
    ``GHA_STATIC_KEYS`` tuples. Catches the most common drift: a new
    key in env/static.env that no handler references."""
    return set(PASSTHROUGH_STATIC_KEYS) | set(GHA_STATIC_KEYS)


class TestStaticYamlDrift(unittest.TestCase):
    def test_every_static_env_key_is_referenced_by_generator(self) -> None:
        static_keys = set(parse_static_env(STATIC_ENV))
        ref_keys = generator_referenced_keys()
        unread = static_keys - ref_keys
        self.assertFalse(
            unread,
            "Keys in env/static.env are not read by any handler under "
            "utils/env/handlers/ (silent drop). Add them to "
            "PASSTHROUGH_STATIC_KEYS or GHA_STATIC_KEYS: "
            f"{sorted(unread)}",
        )

    def test_generator_only_references_existing_static_keys(self) -> None:
        static_keys = set(parse_static_env(STATIC_ENV))
        ref_keys = generator_referenced_keys()
        phantom = ref_keys - static_keys
        self.assertFalse(
            phantom,
            "Generator references keys that do not exist in env/static.env: "
            f"{sorted(phantom)}",
        )


class TestDotenvSmoke(unittest.TestCase):
    """End-to-end: run the generator in a temp dir and check the
    produced .env contains the expected baseline keys."""

    def test_clean_run_produces_expected_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            # Run the generator with a clean env (no INFINITO_DISTRO
            # override, no GITHUB_ACTIONS). The generator always writes
            # to ``<repo-root>/.env``, where repo-root is computed from
            # its own location -- so we redirect via a copy.
            env = {
                k: v
                for k, v in os.environ.items()
                if not k.startswith("INFINITO_")
                and k
                not in (
                    "GITHUB_ACTIONS",
                    "ACT",
                    "VIRTUAL_ENV",
                    "GITHUB_REPOSITORY",
                    "GITHUB_REPOSITORY_OWNER",
                )
            }
            # Re-add PATH so subprocess can find python3, df, etc.
            env.setdefault("PATH", os.environ.get("PATH", ""))

            result = subprocess.run(
                [sys.executable, "-m", "cli.meta.env"],
                env=env,
                cwd=str(PROJECT_ROOT),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"Generator failed: {result.stderr}",
            )

            dotenv = PROJECT_ROOT / ".env"
            self.assertTrue(dotenv.is_file(), "Generator did not produce .env")
            values = parse_dotenv(dotenv)
            missing = EXPECTED_BASELINE_KEYS - set(values)
            self.assertFalse(
                missing,
                f"Generated .env is missing expected baseline keys: {sorted(missing)}",
            )
            # Spot-check derived value
            self.assertEqual(
                values.get("INFINITO_CONTAINER"),
                f"infinito_nexus_{values.get('INFINITO_DISTRO')}",
                "INFINITO_CONTAINER must be infinito_nexus_${INFINITO_DISTRO}",
            )

            # Unused: keep the temp dir reference for tooling
            _ = td


if __name__ == "__main__":
    unittest.main()
