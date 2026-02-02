import unittest
import yaml
import subprocess
from pathlib import Path
from collections import defaultdict


class TestDomainUniqueness(unittest.TestCase):
    def test_no_duplicate_domains(self):
        """
        Load the applications YAML (generating it via `make build` if missing),
        collect all entries under domains.canonical and domains.aliases across all applications,
        and assert that no domain appears more than once.
        """
        repo_root = Path(__file__).resolve().parents[2]
        yaml_file = repo_root / "group_vars" / "all" / "05_applications.yml"

        # Generate the file if it doesn't exist
        if not yaml_file.exists():
            subprocess.run(["make", "build"], cwd=repo_root, check=True)

        # Load the applications configuration
        cfg = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
        apps = cfg.get("defaults_applications", {})

        domain_to_apps = defaultdict(set)

        for app_name, app_cfg in apps.items():
            domains_cfg = app_cfg.get("server", {}).get("domains", {})

            # canonical entries may be a list or a mapping
            canonical = domains_cfg.get("canonical", [])
            if isinstance(canonical, dict):
                values = list(canonical.values())
            else:
                values = canonical or []

            for d in values:
                if isinstance(d, str) and d.strip():
                    domain_to_apps[d].add(app_name)

            # aliases entries may be a list or a mapping
            aliases = domains_cfg.get("aliases", [])
            if isinstance(aliases, dict):
                values = list(aliases.values())
            else:
                values = aliases or []

            for d in values:
                if isinstance(d, str) and d.strip():
                    domain_to_apps[d].add(app_name)

        # Find duplicates: domains that appear in more than one app
        duplicates = {
            domain: list(apps)
            for domain, apps in domain_to_apps.items()
            if len(apps) > 1
        }
        if duplicates:
            details = "\n".join(
                f"Domain '{domain}' is used in applications: {apps}"
                for domain, apps in duplicates.items()
            )
            self.fail(
                f"Duplicate domain entries found:\n{details}\n(Maybe 'make build' solves this issue.)"
            )


if __name__ == "__main__":
    unittest.main()
