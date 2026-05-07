"""Validate `lookup('config', <var>, '<path>')` calls whose path is a
literal but whose application argument is templated. The path must
exist somewhere in the project (any application, any schema). For a
stricter per-role check see :mod:`test_role_local_paths`."""

import unittest
from collections.abc import Mapping

from ._scan import get_scan
from ._validate import PathNotFound, assert_nested


class TestVariablePaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = get_scan()

    def test_variable_paths(self):
        scan = self.scan
        if not scan.variable_paths:
            self.skipTest("No dynamic lookup('config', ...) calls")
        failures: list[str] = []
        for dotted, occs in scan.variable_paths.items():
            if self._resolves_anywhere(dotted):
                continue
            file_path, lineno = occs[0]
            failures.append(f"No entry for '{dotted}'; called at {file_path}:{lineno}")
        if failures:
            self.fail(
                f"{len(failures)} variable lookup path(s) without any match:\n"
                + "\n".join(f"- {f}" for f in failures)
            )

    def _resolves_anywhere(self, dotted: str) -> bool:
        scan = self.scan
        # Schema-defined entries: acceptable in any role schema.
        for schema in scan.role_schemas.values():
            if isinstance(schema, Mapping) and dotted in schema:
                return True

        # Wildcard prefix path: `'a.b.'` matches any role whose nested
        # `a.b.*` mapping exists.
        if dotted.endswith("."):
            prefix_keys = dotted.rstrip(".").split(".")
            for cfg in scan.application_defaults.values():
                cur = cfg
                ok = True
                for p in prefix_keys:
                    if isinstance(cur, Mapping) and p in cur:
                        cur = cur[p]
                    else:
                        ok = False
                        break
                if ok:
                    return True

        if dotted.startswith("credentials."):
            key = dotted.split(".", 1)[1]
            for cfg in scan.application_defaults.values():
                creds = cfg.get("credentials", {}) if isinstance(cfg, Mapping) else {}
                if isinstance(creds, Mapping) and key in creds:
                    return True
            for schema in scan.role_schemas.values():
                creds = schema.get("credentials", {}) if isinstance(schema, Mapping) else {}
                if isinstance(creds, Mapping) and key in creds:
                    return True

        if dotted.startswith("images."):
            if any(
                isinstance(cfg.get("images"), Mapping)
                for cfg in scan.application_defaults.values()
            ):
                return True

        if dotted.startswith("users."):
            subpath = dotted.split(".", 1)[1]
            try:
                assert_nested(scan.user_defaults, subpath, "user_defaults")
                return True
            except PathNotFound:
                pass

        for cfg in scan.application_defaults.values():
            try:
                assert_nested(cfg, dotted, "application_defaults")
                return True
            except PathNotFound:
                pass
        return False


if __name__ == "__main__":
    unittest.main()
