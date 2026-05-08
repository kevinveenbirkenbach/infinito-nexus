"""Lint guard: app-only ``meta/`` files MUST NOT live on non-app roles.

Some artefacts under ``roles/<role>/meta/`` only carry meaning when the
role declares an ``application_id`` in ``vars/main.yml`` and is therefore
deployable as a primary app via ``--apps``. The canonical mapping lives
in :mod:`utils.roles.applications.files` so this lint and the
variant-coverage lint share one source of truth for "what counts as
app-only".

Detection
---------

For every role under ``roles/`` whose ``vars/main.yml.application_id``
is missing or empty the lint walks
:data:`utils.roles.applications.files.APPLICATION_ONLY_META_FILES` and
fails when any of those files exists. Each failure carries the human
description from the SPOT so the reader sees why the file is restricted
without chasing back to commit history.

Fix paths
---------

* If the role IS supposed to be app-targetable, declare a real
  ``application_id`` in its ``vars/main.yml``.
* If the role is genuinely not an application, drop the file and move
  any load-bearing content to a non-app-only home (lifecycle and
  ``run_after`` legitimately stay in ``meta/services.yml``, which is
  NOT app-only and therefore not on the SPOT list).
"""

from __future__ import annotations

import unittest

from utils.roles.applications.files import (
    APPLICATION_ONLY_META_FILES,
    is_application_role,
)

from . import PROJECT_ROOT

_ROLES_DIR = PROJECT_ROOT / "roles"


class TestAppOnlyFiles(unittest.TestCase):
    def test_non_app_roles_have_no_app_only_meta_files(self):
        offenders: list[str] = []

        for role_dir in sorted(p for p in _ROLES_DIR.iterdir() if p.is_dir()):
            if is_application_role(role_dir):
                continue
            for filename, description in APPLICATION_ONLY_META_FILES.items():
                meta_file = role_dir / "meta" / filename
                if meta_file.is_file():
                    rel = meta_file.relative_to(PROJECT_ROOT)
                    offenders.append(f"{rel}\n      {description}")

        if offenders:
            self.fail(
                f"{len(offenders)} app-only meta file(s) found on roles "
                "that do not declare an application_id (declare one in "
                "vars/main.yml or move/remove the file):\n"
                + "\n".join(f"  - {o}" for o in offenders)
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
