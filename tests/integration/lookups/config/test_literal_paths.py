"""Validate every literal `lookup('config', '<app_id>', '<path>')` call
resolves against the role's application defaults / schema."""

import unittest

from utils.applications.config import ConfigEntryNotSetError, get

from ._scan import get_scan
from ._validate import PathNotFound, validate_app_path


class TestLiteralPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = get_scan()

    def test_literal_paths(self):
        scan = self.scan
        failures: list[str] = []
        missing_apps: list[str] = []
        for app_id, paths in scan.literal_paths.items():
            if app_id not in scan.application_defaults:
                missing_apps.append(app_id)
                continue
            for dotted, occs in paths.items():
                try:
                    get(
                        applications=scan.application_defaults,
                        application_id=app_id,
                        config_path=dotted,
                        strict=True,
                    )
                except ConfigEntryNotSetError:
                    continue
                except Exception:
                    pass
                try:
                    validate_app_path(
                        scan.application_defaults,
                        scan.role_schemas,
                        scan.user_defaults,
                        app_id,
                        dotted,
                    )
                except PathNotFound as exc:
                    file_path, lineno = occs[0]
                    failures.append(f"{exc}; called at {file_path}:{lineno}")

        report: list[str] = []
        if missing_apps:
            report.append(
                f"{len(missing_apps)} application id(s) referenced by literal "
                f"lookups but missing in application defaults:"
            )
            report.extend(f"- {a}" for a in sorted(set(missing_apps)))
        if failures:
            report.append(f"{len(failures)} literal lookup path mismatch(es):")
            report.extend(f"- {f}" for f in failures)
        if report:
            self.fail("\n".join(report))


if __name__ == "__main__":
    unittest.main()
