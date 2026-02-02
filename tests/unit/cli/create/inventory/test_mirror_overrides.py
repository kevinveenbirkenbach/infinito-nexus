from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ruamel.yaml import YAML

from cli.create.inventory.mirror_overrides import apply_mirror_overrides


class TestApplyMirrorOverrides(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

        self.yaml_rt = YAML(typ="rt")
        self.yaml_rt.preserve_quotes = True

        self.host_vars = self.root / "host_vars.yml"
        self.mirrors = self.root / "mirrors.yml"

    def _write_yaml(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            self.yaml_rt.dump(data, f)

    def _read_yaml(self, path: Path) -> dict:
        with path.open("r", encoding="utf-8") as f:
            doc = self.yaml_rt.load(f)
        if doc is None:
            return {}
        # ruamel returns CommentedMap; cast to dict for easy assertions
        return dict(doc)

    def test_overwrites_only_image_and_version(self) -> None:
        # host vars has existing app/service with extra keys
        host_vars_data = {
            "applications": {
                "web-app-nextcloud": {
                    "docker": {
                        "services": {
                            "app": {
                                "image": "docker.io/library/nextcloud",
                                "version": "30.0.0",
                                "env": {"FOO": "bar"},
                                "replicas": 2,
                            }
                        }
                    }
                }
            }
        }

        mirrors_data = {
            "applications": {
                "web-app-nextcloud": {
                    "docker": {
                        "services": {
                            "app": {
                                "image": "ghcr.io/acme/mirror/nextcloud",
                                "version": "30.0.1",
                            }
                        }
                    }
                }
            }
        }

        self._write_yaml(self.host_vars, host_vars_data)
        self._write_yaml(self.mirrors, mirrors_data)

        apply_mirror_overrides(self.host_vars, self.mirrors)

        out = self._read_yaml(self.host_vars)
        svc = out["applications"]["web-app-nextcloud"]["docker"]["services"]["app"]

        # overwritten keys
        self.assertEqual(svc["image"], "ghcr.io/acme/mirror/nextcloud")
        self.assertEqual(svc["version"], "30.0.1")

        # preserved keys
        self.assertEqual(svc["env"], {"FOO": "bar"})
        self.assertEqual(svc["replicas"], 2)

    def test_creates_missing_app_and_service(self) -> None:
        # host vars initially empty-ish
        host_vars_data = {"TLS_ENABLED": True}

        mirrors_data = {
            "applications": {
                "svc-db-postgres": {
                    "docker": {
                        "services": {
                            "postgres": {
                                "image": "ghcr.io/acme/mirror/postgres",
                                "version": "16",
                            }
                        }
                    }
                }
            }
        }

        self._write_yaml(self.host_vars, host_vars_data)
        self._write_yaml(self.mirrors, mirrors_data)

        apply_mirror_overrides(self.host_vars, self.mirrors)

        out = self._read_yaml(self.host_vars)

        # unrelated top-level keys preserved
        self.assertTrue(out["TLS_ENABLED"])

        # new structure created
        svc = out["applications"]["svc-db-postgres"]["docker"]["services"]["postgres"]
        self.assertEqual(svc["image"], "ghcr.io/acme/mirror/postgres")
        self.assertEqual(svc["version"], "16")

    def test_ignores_entries_without_image_or_version(self) -> None:
        host_vars_data = {
            "applications": {
                "web-app-nextcloud": {
                    "docker": {"services": {"app": {"image": "x", "version": "1"}}}
                }
            }
        }

        mirrors_data = {
            "applications": {
                "web-app-nextcloud": {
                    "docker": {
                        "services": {
                            "app": {
                                "image": "ghcr.io/acme/mirror/nextcloud",
                                # missing version -> should be ignored
                            }
                        }
                    }
                },
                "web-app-wordpress": {
                    "docker": {
                        "services": {
                            "wp": {
                                # missing image -> ignored
                                "version": "6.4",
                            }
                        }
                    }
                },
            }
        }

        self._write_yaml(self.host_vars, host_vars_data)
        self._write_yaml(self.mirrors, mirrors_data)

        apply_mirror_overrides(self.host_vars, self.mirrors)

        out = self._read_yaml(self.host_vars)

        # nextcloud unchanged because mirror entry incomplete
        svc_nc = out["applications"]["web-app-nextcloud"]["docker"]["services"]["app"]
        self.assertEqual(svc_nc["image"], "x")
        self.assertEqual(svc_nc["version"], "1")

        # wordpress should not have been created because mirror entry incomplete
        self.assertNotIn("web-app-wordpress", out.get("applications", {}))

    def test_noop_when_mirrors_has_no_applications(self) -> None:
        host_vars_data = {
            "applications": {
                "a": {"docker": {"services": {"s": {"image": "i", "version": "v"}}}}
            }
        }
        mirrors_data = {"not_applications": {"x": 1}}

        self._write_yaml(self.host_vars, host_vars_data)
        self._write_yaml(self.mirrors, mirrors_data)

        apply_mirror_overrides(self.host_vars, self.mirrors)

        out = self._read_yaml(self.host_vars)
        svc = out["applications"]["a"]["docker"]["services"]["s"]
        self.assertEqual(svc["image"], "i")
        self.assertEqual(svc["version"], "v")

    def test_raises_system_exit_if_mirrors_file_missing(self) -> None:
        self._write_yaml(self.host_vars, {"applications": {}})

        missing = self.root / "does-not-exist.yml"
        with self.assertRaises(SystemExit):
            apply_mirror_overrides(self.host_vars, missing)


if __name__ == "__main__":
    unittest.main()
