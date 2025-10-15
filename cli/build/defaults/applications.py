#!/usr/bin/env python3
import argparse
import yaml
import sys
import time
from pathlib import Path

# Ensure project root on PYTHONPATH so module_utils is importable
repo_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

# Add lookup_plugins for application_gid
plugin_path = repo_root / "lookup_plugins"
sys.path.insert(0, str(plugin_path))

from module_utils.dict_renderer import DictRenderer
from application_gid import LookupModule

def load_yaml_file(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

class DefaultsGenerator:
    def __init__(self, roles_dir: Path, output_file: Path, verbose: bool, timeout: float):
        self.roles_dir = roles_dir
        self.output_file = output_file
        self.verbose = verbose
        self.renderer = DictRenderer(verbose=verbose, timeout=timeout)
        self.gid_lookup = LookupModule()

    def log(self, message: str):
        if self.verbose:
            print(f"[DefaultsGenerator] {message}")

    def run(self):
        result = {"defaults_applications": {}}

        for role_dir in sorted(self.roles_dir.iterdir()):
            role_name = role_dir.name
            vars_main = role_dir / "vars" / "main.yml"
            config_file = role_dir / "config" / "main.yml"

            if not vars_main.exists():
                self.log(f"Skipping {role_name}: vars/main.yml missing")
                continue

            vars_data = load_yaml_file(vars_main)
            application_id = vars_data.get("application_id")
            if not application_id:
                self.log(f"Skipping {role_name}: application_id not defined")
                continue

            if not config_file.exists():
                self.log(f"Config missing for {role_name}, adding empty defaults for '{application_id}'")
                result["defaults_applications"][application_id] = {}
                continue

            config_data = load_yaml_file(config_file)
            if config_data:
                try:
                    gid_number = self.gid_lookup.run([application_id], roles_dir=str(self.roles_dir))[0]
                except Exception as e:
                    print(f"Warning: failed to determine gid for '{application_id}': {e}", file=sys.stderr)
                    sys.exit(1)

                config_data["group_id"] = gid_number
                result["defaults_applications"][application_id] = config_data

                # Inject users mapping as Jinja2 references
                users_meta = load_yaml_file(role_dir / "users" / "main.yml")
                users_data = users_meta.get("users", {})
                transformed = {user: f"{{{{ users[\"{user}\"] }}}}" for user in users_data}
                if transformed:
                    result["defaults_applications"][application_id]["users"] = transformed

        # Render placeholders in entire result context
        self.log("Starting placeholder rendering...")
        try:
            result = self.renderer.render(result)
        except Exception as e:
            print(f"Error during rendering: {e}", file=sys.stderr)
            sys.exit(1)

        # Sort applications by application key for stable output
        apps = result.get("defaults_applications", {})
        if isinstance(apps, dict) and apps:
            result["defaults_applications"] = {
                k: apps[k] for k in sorted(apps.keys())
            }

        # Write output
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with self.output_file.open("w", encoding="utf-8") as f:
            yaml.dump(result, f, sort_keys=False)

        # Print location of generated file (absolute if not under cwd)
        try:
            rel = self.output_file.relative_to(Path.cwd())
        except ValueError:
            rel = self.output_file
        print(f"✅ Generated: {rel}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate defaults_applications YAML...")
    parser.add_argument("--roles-dir", default="roles", help="Path to the roles directory")
    parser.add_argument("--output-file", required=True, help="Path to output YAML file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--timeout", type=float, default=10.0, help="Timeout for rendering")

    args = parser.parse_args()
    cwd = Path.cwd()
    roles_dir = (cwd / args.roles_dir).resolve()
    output_file = (cwd / args.output_file).resolve()

    DefaultsGenerator(roles_dir, output_file, args.verbose, args.timeout).run()
