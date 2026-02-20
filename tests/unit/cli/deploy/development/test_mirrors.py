from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from cli.deploy.development.mirrors import generate_ci_mirrors_file


class TestGenerateCiMirrorsFile(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {
            "RUNNING_ON_GITHUB": "true",
            "GITHUB_REPOSITORY_OWNER": "kevinveenbirkenbach",
            "INFINITO_GHCR_MIRROR_PREFIX": "mirror",
        },
        clear=False,
    )
    def test_uses_container_python_from_env_with_fallback(self) -> None:
        compose = MagicMock()

        out = generate_ci_mirrors_file(compose, inventory_dir="/tmp/inventory")

        self.assertEqual(out, "/tmp/inventory/mirrors.yml")
        compose.exec.assert_called_once()

        called_cmd = compose.exec.call_args.args[0]
        self.assertEqual(called_cmd[0:2], ["sh", "-lc"])
        self.assertIn('"${PYTHON:-python3}" -m cli.mirror.resolver', called_cmd[2])
        self.assertNotIn("python3 -m cli.mirror.resolver", called_cmd[2])

    @patch.dict("os.environ", {}, clear=True)
    def test_raises_on_missing_required_env(self) -> None:
        compose = MagicMock()

        with self.assertRaises(RuntimeError):
            generate_ci_mirrors_file(compose, inventory_dir="/tmp/inventory")

        compose.exec.assert_not_called()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
