import unittest
import types
from pathlib import Path
from unittest.mock import patch
import subprocess
import os


def load_module():
    """
    Dynamically load the target script:
    roles/svc-bkp-rmt-2-loc/files/pull-specific-host.py
    relative to this test file.
    """
    here = Path(__file__).resolve()
    # tests/unit/roles/svc-bkp-rmt-2-loc/files -> up 5 levels to repo root
    repo_root = here.parents[5]
    target_path = repo_root / "roles" / "svc-bkp-rmt-2-loc" / "files" / "pull-specific-host.py"
    if not target_path.exists():
        raise FileNotFoundError(f"Cannot find script at {target_path}")
    spec = types.ModuleType("pull_specific_host_module")
    code = target_path.read_text(encoding="utf-8")
    exec(compile(code, str(target_path), "exec"), spec.__dict__)
    return spec


class PullSpecificHostTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.hash64 = "a" * 64
        self.host = "1.2.3.4"
        self.remote = f"backup@{self.host}"
        self.base = f"/Backups/{self.hash64}/"
        self.backup_type = "backup-docker-to-local"
        self.type_dir = f"{self.base}{self.backup_type}/"
        self.last_local = f"{self.type_dir}20250101000000"
        self.last_remote = f"{self.type_dir}20250202000000"

    def _completed(self, stdout="", returncode=0):
        return subprocess.CompletedProcess(args="mock", returncode=returncode, stdout=stdout, stderr="")

    def _run_side_effect_success(self, command, capture_output=True, shell=True, text=True, check=False):
        cmd = command if isinstance(command, str) else " ".join(command)
        if cmd.startswith(f'ssh "{self.remote}" sha256sum /etc/machine-id'):
            return self._completed(stdout=f"{self.hash64}  /etc/machine-id\n")
        if cmd.startswith(f'ssh "{self.remote}" "find {self.base} -maxdepth 1 -type d -execdir basename {{}} ;"'):
            return self._completed(stdout=f"{self.hash64}\n{self.backup_type}\n")
        if cmd.startswith(f"ls -d {self.type_dir}* | tail -1"):
            return self._completed(stdout=self.last_local)
        if cmd.startswith(f'ssh "{self.remote}" "ls -d {self.type_dir}*'):
            return self._completed(stdout=f"{self.last_remote}\n")
        return self._completed(stdout="")

    def _run_side_effect_find_fail(self, command, capture_output=True, shell=True, text=True, check=False):
        cmd = command if isinstance(command, str) else " ".join(command)
        if cmd.startswith(f'ssh "backup@{self.host}" "find {self.base} -maxdepth 1 -type d -execdir basename {{}} ;"'):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd, output="", stderr="find: error")
        if cmd.startswith(f'ssh "backup@{self.host}" sha256sum /etc/machine-id'):
            return self._completed(stdout=f"{self.hash64}  /etc/machine-id\n")
        return self._completed(stdout="")

    def _run_side_effect_no_types(self, command, capture_output=True, shell=True, text=True, check=False):
        cmd = command if isinstance(command, str) else " ".join(command)
        if cmd.startswith(f'ssh "{self.remote}" sha256sum /etc/machine-id'):
            return self._completed(stdout=f"{self.hash64}  /etc/machine-id\n")
        if cmd.startswith(f'ssh "{self.remote}" "find {self.base} -maxdepth 1 -type d -execdir basename {{}} ;"'):
            return self._completed(stdout="")
        return self._completed(stdout="")

    @patch("time.sleep", new=lambda *a, **k: None)
    @patch.object(os, "makedirs")
    @patch.object(os, "system")
    @patch.object(subprocess, "run")
    def test_success_rsync_zero_exit(self, mock_run, mock_system, _mkd):
        mock_run.side_effect = self._run_side_effect_success
        mock_system.return_value = 0
        with self.assertRaises(SystemExit) as cm:
            self.mod.pull_backups(self.host)
        self.assertEqual(cm.exception.code, 0)
        self.assertTrue(mock_system.called, "rsync (os.system) should be called")

    @patch("time.sleep", new=lambda *a, **k: None)
    @patch.object(os, "makedirs")
    @patch.object(os, "system")
    @patch.object(subprocess, "run")
    def test_no_backup_types_exit_zero(self, mock_run, mock_system, _mkd):
        mock_run.side_effect = self._run_side_effect_no_types
        mock_system.return_value = 0
        with self.assertRaises(SystemExit) as cm:
            self.mod.pull_backups(self.host)
        self.assertEqual(cm.exception.code, 0)
        self.assertFalse(mock_system.called, "rsync should not be called when no types found")

    @patch("time.sleep", new=lambda *a, **k: None)
    @patch.object(os, "makedirs")
    @patch.object(os, "system")
    @patch.object(subprocess, "run")
    def test_find_failure_exits_one(self, mock_run, mock_system, _mkd):
        mock_run.side_effect = self._run_side_effect_find_fail
        mock_system.return_value = 0
        with self.assertRaises(SystemExit) as cm:
            self.mod.pull_backups(self.host)
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(mock_system.called, "rsync should not be called when find fails")

    @patch("time.sleep", new=lambda *a, **k: None)
    @patch.object(os, "makedirs")
    @patch.object(os, "system")
    @patch.object(subprocess, "run")
    def test_rsync_fails_after_retries_exit_nonzero(self, mock_run, mock_system, _mkd):
        mock_run.side_effect = self._run_side_effect_success
        mock_system.side_effect = [1] * 12  # 12 retries in the script
        with self.assertRaises(SystemExit) as cm:
            self.mod.pull_backups(self.host)
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(mock_system.call_count, 12, "rsync should have retried 12 times")


if __name__ == "__main__":
    unittest.main()
