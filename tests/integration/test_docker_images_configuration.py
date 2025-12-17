import unittest
import yaml
from pathlib import Path

class TestDockerRoleServicesConfiguration(unittest.TestCase):
    def test_services_keys_and_templates(self):
        """
        For each web-app-* role, check that:
        - roles/web-app-*/config/main.yml contains 'services' as a dict with keys/values
        """
        repo_root = Path(__file__).resolve().parent.parent.parent
        roles_dir = repo_root / "roles"
        errors = []
        warnings = []

        for role_path in roles_dir.iterdir():
            if not (role_path.is_dir() and role_path.name.startswith("web-app-")):
                continue

            cfg_file = role_path / "config" / "main.yml"
            if not cfg_file.exists():
                continue  # No configuration to check

            try:
                config = yaml.safe_load(cfg_file.read_text("utf-8")) or {}
                main_file = role_path / "vars" / "main.yml"
                yaml.safe_load(main_file.read_text("utf-8")) or {}
            except yaml.YAMLError as e:
                errors.append(f"{role_path.name}: YAML parse error: {e}")
                continue

            services = config.get("docker",{}).get("services",{})
            if not services:
                warnings.append(f"[WARNING] {role_path.name}: No 'docker.services' key in config/main.yml")
                continue

            if not isinstance(services, dict):
                errors.append(f"{role_path.name}: 'services' must be a dict in config/main.yml")
                continue

                # OPTIONAL: Check if the image is available locally via docker images
                # from shutil import which
                # import subprocess
                # if which("docker"):
                #     try:
                #         out = subprocess.check_output(
                #             ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"]
                #         ).decode()
                #         if value not in out:
                #             errors.append(f"{role_path.name}: Image '{value}' not found locally (optional check)")
                #     except Exception as e:
                #         errors.append(f"{role_path.name}: Error running 'docker images' (optional): {e}")
        if warnings:
            print("\nWarnings in docker role services configuration:\n" + "\n".join(warnings))
        if errors:
            self.fail("Errors in docker role services configuration:\n" + "\n".join(errors))

if __name__ == "__main__":
    unittest.main()
