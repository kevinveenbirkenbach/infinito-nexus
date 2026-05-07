"""Strict per-role check for `lookup('config', <var>, 'literal.path')`.

When a role file (under `roles/<role>/...`) calls
`lookup('config', application_id, 'a.b.c')`, the path must resolve
against `application_defaults[<role>]` — not merely against *some*
role, which is all :mod:`test_variable_paths` guarantees.
`application_id` is always equal to the role name in this repo (set in
`roles/<role>/vars/main.yml`), so the file-path-derived role is the
correct lookup context.

Mirrors the resolution logic of `plugins/lookup/config.py`:
- `users.<canonical>.<sub>`: requires the role's `meta/users.yml` to
  declare `<canonical>` AND the global `user_defaults[<canonical>]` to
  expose `<sub>`.
- `credentials.<key>` / `images.<key>`: same fallbacks as the
  literal-paths check.
- everything else: must walk the role's `application_defaults` entry.
"""

import unittest
from collections.abc import Mapping

from ._scan import get_scan
from ._validate import PathNotFound, assert_nested, validate_app_path


class TestRoleLocalLiteralPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = get_scan()

    def test_role_local_literal_paths(self):
        scan = self.scan
        if not scan.role_local_paths:
            self.skipTest("No role-local lookup('config', <var>, 'literal') calls")
        failures: list[str] = []
        for (role_id, dotted), occs in scan.role_local_paths.items():
            if role_id not in scan.application_defaults:
                continue
            cfg = scan.application_defaults[role_id]
            if dotted.startswith("users."):
                err = self._check_users_path(role_id, cfg, dotted, occs)
                if err:
                    failures.append(err)
                continue
            try:
                validate_app_path(
                    scan.application_defaults,
                    scan.role_schemas,
                    scan.user_defaults,
                    role_id,
                    dotted,
                )
            except PathNotFound as exc:
                file_path, lineno = occs[0]
                failures.append(f"{exc}; called at {file_path}:{lineno}")
        if failures:
            self.fail(
                f"{len(failures)} role-local lookup path mismatch(es):\n"
                + "\n".join(f"- {f}" for f in failures)
            )

    def _check_users_path(self, role_id, cfg, dotted, occs) -> str | None:
        sub_parts = dotted.split(".", 2)
        if len(sub_parts) < 2:
            return None
        canonical = sub_parts[1]
        file_path, lineno = occs[0]
        role_users = cfg.get("users") if isinstance(cfg, Mapping) else None
        if not isinstance(role_users, Mapping):
            return (
                f"role '{role_id}' references '{dotted}' but has no users "
                f"mapping (declare '{canonical}' in roles/{role_id}/meta/"
                f"users.yml); called at {file_path}:{lineno}"
            )
        if canonical not in role_users:
            return (
                f"role '{role_id}' references '{dotted}' but '{canonical}' is "
                f"not declared in roles/{role_id}/meta/users.yml; called at "
                f"{file_path}:{lineno}"
            )
        if len(sub_parts) == 3:
            try:
                assert_nested(
                    self.scan.user_defaults,
                    f"{canonical}.{sub_parts[2]}",
                    "user_defaults",
                )
            except PathNotFound as exc:
                return f"role '{role_id}': {exc}; called at {file_path}:{lineno}"
        return None


if __name__ == "__main__":
    unittest.main()
