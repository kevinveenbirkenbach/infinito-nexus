from __future__ import annotations

import importlib.util
import os
import unittest
from copy import deepcopy
from pathlib import Path
from types import ModuleType


REL_PLUGIN_PATH = Path("roles/sys-token-store/filter_plugins/token_store.py")


def _find_plugin_path() -> Path:
    """
    Find the plugin file by walking upwards and checking the expected relative path.

    This avoids accidentally picking tests/unit as "repo root" just because it
    contains a 'roles/' directory for test organization.
    """
    # Optional explicit override for CI/local runs
    env_root = os.environ.get("INFINITO_REPO_ROOT", "").strip()
    if env_root:
        candidate = Path(env_root).resolve() / REL_PLUGIN_PATH
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"INFINITO_REPO_ROOT set but plugin not found at: {candidate}")

    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        candidate = parent / REL_PLUGIN_PATH
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        "token_store.py not found while walking up directories. "
        f"Expected relative path: {REL_PLUGIN_PATH}. "
        "You can set INFINITO_REPO_ROOT to your repository root."
    )


def _load_token_store_module() -> ModuleType:
    plugin_path = _find_plugin_path()

    spec = importlib.util.spec_from_file_location("token_store_plugin", str(plugin_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to create import spec for: {plugin_path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_TOKEN_STORE = _load_token_store_module()
hydrate_users_tokens = _TOKEN_STORE.hydrate_users_tokens


class TestTokenStoreHydration(unittest.TestCase):
    def test_returns_users_unchanged_when_store_empty(self) -> None:
        users = {"alice": {"tokens": {"app1": "u1"}}}
        out = hydrate_users_tokens(users, {})
        self.assertEqual(out, users)

    def test_store_fills_missing_user_and_token(self) -> None:
        users = {}
        store = {"alice": {"tokens": {"app1": "s1"}}}
        out = hydrate_users_tokens(users, store)
        self.assertEqual(out["alice"]["tokens"]["app1"], "s1")

    def test_store_fills_missing_token_but_keeps_existing_other_tokens(self) -> None:
        users = {"alice": {"tokens": {"app2": "u2"}}}
        store = {"alice": {"tokens": {"app1": "s1"}}}
        out = hydrate_users_tokens(users, store)
        self.assertEqual(out["alice"]["tokens"]["app2"], "u2")
        self.assertEqual(out["alice"]["tokens"]["app1"], "s1")

    def test_store_overwrites_only_if_users_token_effectively_empty(self) -> None:
        for user_value in (None, "", "   ", "\n\t "):
            with self.subTest(user_value=user_value):
                users = {"alice": {"tokens": {"app1": user_value}}}
                store = {"alice": {"tokens": {"app1": "s1"}}}
                out = hydrate_users_tokens(users, store)
                self.assertEqual(out["alice"]["tokens"]["app1"], "s1")

    def test_users_wins_if_non_empty_after_strip(self) -> None:
        for user_value in ("u1", "  u1  ", 123):
            with self.subTest(user_value=user_value):
                users = {"alice": {"tokens": {"app1": user_value}}}
                store = {"alice": {"tokens": {"app1": "s1"}}}
                out = hydrate_users_tokens(users, store)

                # Users wins; implementation keeps original user value (no stripping)
                self.assertEqual(out["alice"]["tokens"]["app1"], user_value)

    def test_empty_store_tokens_are_ignored(self) -> None:
        for store_value in (None, "", "   ", "\n"):
            with self.subTest(store_value=store_value):
                users = {"alice": {"tokens": {}}}
                store = {"alice": {"tokens": {"app1": store_value}}}
                out = hydrate_users_tokens(users, store)
                self.assertEqual(out["alice"]["tokens"], {})

    def test_ignores_non_mapping_store_user_data(self) -> None:
        users = {}
        store = {"alice": "not-a-dict", "bob": {"tokens": {"app1": "s1"}}}
        out = hydrate_users_tokens(users, store)
        self.assertNotIn("alice", out)
        self.assertEqual(out["bob"]["tokens"]["app1"], "s1")

    def test_ignores_non_mapping_store_tokens(self) -> None:
        users = {"alice": {}}
        store = {"alice": {"tokens": "not-a-dict"}}
        out = hydrate_users_tokens(users, store)
        self.assertEqual(out["alice"].get("tokens", {}), {})

    def test_does_not_mutate_inputs(self) -> None:
        users = {"alice": {"tokens": {"app1": "   "}}}
        store = {"alice": {"tokens": {"app1": "s1"}}}

        users_before = deepcopy(users)
        store_before = deepcopy(store)

        out = hydrate_users_tokens(users, store)

        self.assertEqual(out["alice"]["tokens"]["app1"], "s1")
        self.assertEqual(users, users_before)
        self.assertEqual(store, store_before)


if __name__ == "__main__":
    unittest.main()
