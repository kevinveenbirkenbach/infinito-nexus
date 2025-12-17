import unittest
import os
import shutil

# Import the filter directly
from filter_plugins.has_env import has_env


class TestHasEnvFilter(unittest.TestCase):
    def setUp(self):
        # Create a test directory structure
        self.base_dir = "./testdata"
        self.app_with_env = "app_with_env"
        self.app_without_env = "app_without_env"
        os.makedirs(
            os.path.join(self.base_dir, "roles", self.app_with_env, "templates"),
            exist_ok=True,
        )
        os.makedirs(
            os.path.join(self.base_dir, "roles", self.app_without_env, "templates"),
            exist_ok=True,
        )

        # Create an empty env.j2 file
        with open(
            os.path.join(
                self.base_dir, "roles", self.app_with_env, "templates", "env.j2"
            ),
            "w",
        ) as f:
            f.write("")

    def tearDown(self):
        # Clean up the test data
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)

    def test_env_exists(self):
        """Test that has_env returns True if env.j2 exists."""
        self.assertTrue(has_env(self.app_with_env, base_dir=self.base_dir))

    def test_env_not_exists(self):
        """Test that has_env returns False if env.j2 does not exist."""
        self.assertFalse(has_env(self.app_without_env, base_dir=self.base_dir))


if __name__ == "__main__":
    unittest.main()
