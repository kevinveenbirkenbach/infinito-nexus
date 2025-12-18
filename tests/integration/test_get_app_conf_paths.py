# tests/integration/test_get_app_conf_paths.py

import os
import re
import unittest
from pathlib import Path

import yaml  # requires PyYAML
from filter_plugins.get_role import get_role
from filter_plugins.get_app_conf import get_app_conf, ConfigEntryNotSetError


class TestGetAppConfPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup paths
        root = Path(__file__).resolve().parents[2]
        cls.root = root
        cls.app_config_path = root / "group_vars" / "all" / "04_applications.yml"
        cls.user_config_path = root / "group_vars" / "all" / "03_users.yml"

        # Load application defaults
        with cls.app_config_path.open(encoding="utf-8") as f:
            app_cfg = yaml.safe_load(f) or {}
        cls.defaults_app = app_cfg.get("defaults_applications", {})

        # Load default users
        with cls.user_config_path.open(encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        cls.defaults_users = user_cfg.get("default_users", {})

        # Preload role schemas: map application_id -> schema dict
        cls.role_schemas = {}
        cls.role_for_app = {}
        roles_path = str(root / "roles")
        for app_id in cls.defaults_app:
            try:
                role = get_role(app_id, roles_path)
                cls.role_for_app[app_id] = role
                schema_file = root / "roles" / role / "schema" / "main.yml"
                with schema_file.open(encoding="utf-8") as sf:
                    schema = yaml.safe_load(sf) or {}
                cls.role_schemas[app_id] = schema
            except Exception:
                # skip apps without schema or role
                continue

        # Regex to find get_app_conf calls
        cls.pattern = re.compile(
            r"get_app_conf\(\s*([^\),]+)\s*,\s*['\"]([^'\"]+)['\"]"
        )

        # Scan files once
        cls.literal_paths = {}  # app_id -> {path: [(file,line)...]}
        cls.variable_paths = {}  # path -> [(file,line)...]

        for dirpath, dirs, files in os.walk(root):
            # skip descending into the tests directory
            if "tests" in dirs:
                dirs.remove("tests")
            if "tests" in Path(dirpath).parts:
                continue
            for fname in files:
                # ignore .py and .sh files
                if fname.endswith((".py", ".sh")):
                    continue
                file_path = Path(dirpath) / fname
                try:
                    text = file_path.read_text(encoding="utf-8")
                except Exception:
                    continue
                for m in cls.pattern.finditer(text):
                    # Determine the start and end of the current line
                    start = text.rfind("\n", 0, m.start()) + 1
                    end = text.find("\n", start)
                    line = text[start:end] if end != -1 else text[start:]

                    # 1) Skip lines that are entirely commented out
                    if line.lstrip().startswith("#"):
                        continue

                    # 2) Skip calls preceded by an inline comment
                    idx_call = line.find("get_app_conf")
                    idx_hash = line.find("#")
                    if 0 <= idx_hash < idx_call:
                        continue
                    lineno = text.count("\n", 0, m.start()) + 1
                    app_arg = m.group(1).strip()
                    path_arg = m.group(2).strip()
                    # ignore any templated Jinja2 raw-blocks
                    if "{%" in path_arg:
                        continue
                    if (app_arg.startswith("'") and app_arg.endswith("'")) or (
                        app_arg.startswith('"') and app_arg.endswith('"')
                    ):
                        app_id = app_arg.strip("'\"")
                        cls.literal_paths.setdefault(app_id, {}).setdefault(
                            path_arg, []
                        ).append((file_path, lineno))
                    else:
                        cls.variable_paths.setdefault(path_arg, []).append(
                            (file_path, lineno)
                        )

    def assertNested(self, mapping, dotted, context):
        keys = dotted.split(".")
        cur = mapping
        for k in keys:
            assert isinstance(cur, dict), f"{context}: expected dict at {k}"
            assert k in cur, f"{context}: missing '{k}' in '{dotted}'"
            cur = cur[k]

    def test_literal_paths(self):
        # Check each literal path exists or is allowed by schema
        for app_id, paths in self.literal_paths.items():
            with self.subTest(app=app_id):
                self.assertIn(
                    app_id,
                    self.defaults_app,
                    f"App '{app_id}' missing in defaults_applications",
                )
                for dotted, occs in paths.items():
                    with self.subTest(path=dotted):
                        try:
                            # will raise ConfigEntryNotSetError if defined in schema but not set
                            get_app_conf(self.defaults_app, app_id, dotted, strict=True)
                        except ConfigEntryNotSetError:
                            # defined in schema but not set: acceptable
                            continue
                        # otherwise, perform static validation
                        self._validate(app_id, dotted, occs)

    def test_variable_paths(self):
        # dynamic paths: must exist somewhere
        if not self.variable_paths:
            self.skipTest("No dynamic get_app_conf calls")
        for dotted, occs in self.variable_paths.items():
            with self.subTest(path=dotted):
                found = False
                # schema-defined entries: acceptable if defined in any role schema
                for schema in self.role_schemas.values():
                    if isinstance(schema, dict) and dotted in schema:
                        found = True
                        break
                if found:
                    continue

                # Wildcard‑prefix: if the path ends with '.', treat it as a prefix
                # and check for nested dicts in defaults_applications
                if dotted.endswith("."):
                    prefix = dotted.rstrip(".")
                    parts = prefix.split(".")
                    for cfg in self.defaults_app.values():
                        cur = cfg
                        ok = True
                        for p in parts:
                            if isinstance(cur, dict) and p in cur:
                                cur = cur[p]
                            else:
                                ok = False
                                break
                        if ok:
                            found = True
                            break
                    if found:
                        continue

                # credentials.*: zuerst in defaults_applications prüfen, dann im Schema
                if dotted.startswith("credentials."):
                    key = dotted.split(".", 1)[1]
                    # 1) defaults_applications[app_id].credentials
                    for aid, cfg in self.defaults_app.items():
                        creds = cfg.get("credentials", {})
                        if isinstance(creds, dict) and key in creds:
                            found = True
                            break
                    if found:
                        continue
                    # 2) role_schema.credentials
                    for aid, schema in self.role_schemas.items():
                        creds = schema.get("credentials", {})
                        if isinstance(creds, dict) and key in creds:
                            found = True
                            break
                    if found:
                        continue
                # images.*: any images dict
                if dotted.startswith("images."):
                    if any(
                        isinstance(cfg.get("images"), dict)
                        for cfg in self.defaults_app.values()
                    ):
                        continue
                # users.*: default_users fallback
                if dotted.startswith("users."):
                    subpath = dotted.split(".", 1)[1]
                    try:
                        # this will raise if the nested key doesn’t exist
                        self.assertNested(self.defaults_users, subpath, "default_users")
                        continue
                    except AssertionError:
                        # It's expected that subpath may not exist in default_users; continue.
                # application defaults
                for aid, cfg in self.defaults_app.items():
                    try:
                        self.assertNested(cfg, dotted, aid)
                        found = True
                        break
                    except AssertionError:
                        # It's expected that not every config dict will have the required nested keys;
                        # try the next config dict until found.
                        pass
                if not found:
                    file_path, lineno = occs[0]
                    self.fail(
                        f"No entry for '{dotted}'; called at {file_path}:{lineno}"
                    )

    def _validate(self, app_id, dotted, occs):
        # try app defaults
        cfg = self.defaults_app.get(app_id, {})
        try:
            self.assertNested(cfg, dotted, app_id)
            return
        except AssertionError:
            pass
        # users.* fallback
        if dotted.startswith("users."):
            sub = dotted.split(".", 1)[1]
            if sub in self.defaults_users:
                return
        # credentials.* fallback: defaults_applications, dann Schema
        if dotted.startswith("credentials."):
            key = dotted.split(".", 1)[1]
            # 1) defaults_applications[app_id].credentials
            creds_cfg = cfg.get("credentials", {})
            if isinstance(creds_cfg, dict) and key in creds_cfg:
                return
            # 2) schema
            schema = self.role_schemas.get(app_id, {})
            creds = schema.get("credentials", {})
            self.assertIn(key, creds, f"Credential '{key}' missing for app '{app_id}'")
            return
        # images.* fallback
        if dotted.startswith("images."):
            if isinstance(cfg.get("images"), dict):
                return
        # final fail
        file_path, lineno = occs[0]
        self.fail(
            f"'{dotted}' not found for '{app_id}'; called at {file_path}:{lineno}"
        )


if __name__ == "__main__":
    unittest.main()
