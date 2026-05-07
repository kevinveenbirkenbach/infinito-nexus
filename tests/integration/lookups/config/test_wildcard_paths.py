"""Validate `~`-concatenated path expressions in `lookup('config', ...)`.

The literal-path scanner only sees the first quoted string and falls
back to wildcard-prefix matching for paths ending in `.`, which is too
permissive. This test reconstructs the full path with `*` placeholders
for every Jinja variable segment and validates the wildcard path
against the same fallback chain the literal-path test uses."""

import unittest
from collections.abc import Mapping

from ._scan import get_scan
from ._validate import match_wildcard_path, match_wildcard_segment


class TestWildcardPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = get_scan()

    def test_wildcard_paths(self):
        scan = self.scan
        if not scan.wildcard_paths:
            self.skipTest("No `~`-concatenated lookup paths found")
        failures: list[str] = []
        for (role_id, wildcard_path), occs in scan.wildcard_paths.items():
            cfg = scan.application_defaults.get(role_id)
            if cfg is None:
                continue
            if self._resolves(cfg, role_id, wildcard_path):
                continue
            file_path, lineno = occs[0]
            failures.append(
                f"wildcard path '{wildcard_path}' has no match in application "
                f"defaults / schema for role '{role_id}'; called at "
                f"{file_path}:{lineno}"
            )
        if failures:
            self.fail(
                f"{len(failures)} wildcard lookup path mismatch(es):\n"
                + "\n".join(f"- {f}" for f in failures)
            )

    def _resolves(self, cfg, role_id: str, wildcard_path: str) -> bool:
        scan = self.scan
        if match_wildcard_path(cfg, wildcard_path):
            return True
        if wildcard_path.startswith("users."):
            sub = wildcard_path.split(".", 1)[1]
            if match_wildcard_path({"_root": scan.user_defaults}, "_root." + sub):
                return True
        if wildcard_path.startswith("credentials."):
            sub = wildcard_path.split(".", 1)[1]
            creds_cfg = cfg.get("credentials")
            if isinstance(creds_cfg, Mapping) and match_wildcard_segment(creds_cfg, sub):
                return True
            schema = scan.role_schemas.get(role_id, {})
            creds = schema.get("credentials") if isinstance(schema, Mapping) else None
            if isinstance(creds, Mapping) and match_wildcard_segment(creds, sub):
                return True
        if wildcard_path.startswith("images.") and isinstance(
            cfg.get("images"), Mapping
        ):
            return True
        return False


if __name__ == "__main__":
    unittest.main()
