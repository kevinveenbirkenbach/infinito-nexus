import os
import tempfile
import unittest
import importlib.util

HERE = os.path.abspath(os.path.dirname(__file__))


def _find_repo_root(start_dir: str, probe_parts: list[str]) -> str:
    """
    Walk upwards from start_dir until a path joined with probe_parts exists.
    Returns the directory considered the repo root.
    """
    cur = os.path.abspath(start_dir)
    for _ in range(15):  # plenty of headroom
        candidate = os.path.join(cur, *probe_parts)
        if os.path.exists(candidate):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    raise RuntimeError(
        f"Could not locate {'/'.join(probe_parts)} starting from {start_dir}"
    )


PROBE = ["roles", "sys-svc-cdn", "filter_plugins", "cdn_paths.py"]
ROOT = _find_repo_root(HERE, PROBE)


def _load_module(mod_name: str, rel_path_from_root: str):
    """Load a python module from an absolute file path (hyphen-safe)."""
    path = os.path.join(ROOT, rel_path_from_root)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader, f"Cannot load spec for {path}"
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


cdn_paths_mod = _load_module(
    "cdn_paths_mod",
    os.path.join("roles", "sys-svc-cdn", "filter_plugins", "cdn_paths.py"),
)
cdn_urls_mod = _load_module(
    "cdn_urls_mod",
    os.path.join("roles", "sys-svc-cdn", "filter_plugins", "cdn_urls.py"),
)
cdn_dirs_mod = _load_module(
    "cdn_dirs_mod",
    os.path.join("roles", "sys-svc-cdn", "filter_plugins", "cdn_dirs.py"),
)


class TestCdnPathsUrlsDirs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.app = "web-app-dashboard"
        self.ver = "20250101"

        self.cdn_paths = cdn_paths_mod.cdn_paths
        self.cdn_urls = cdn_urls_mod.cdn_urls
        self.cdn_dirs = cdn_dirs_mod.cdn_dirs

        self.tree = self.cdn_paths(self.root, self.app, self.ver)

    def tearDown(self):
        self.tmp.cleanup()

    # ---- cdn_paths ----
    def test_paths_shape_and_values(self):
        t = self.tree
        self.assertTrue(os.path.isabs(t["root"]))
        self.assertEqual(t["role"]["id"], self.app)
        self.assertEqual(t["role"]["version"], self.ver)
        self.assertTrue(t["shared"]["css"].endswith(os.path.join("_shared", "css")))
        self.assertTrue(
            t["role"]["release"]["css"].endswith(
                os.path.join(self.app, self.ver, "css")
            )
        )

    # ---- cdn_urls ----
    def test_urls_mapping_and_root_trailing_slash(self):
        base = "https://cdn.example.com"
        urls = self.cdn_urls(self.tree, base)

        # Non-path strings remain untouched
        self.assertEqual(urls["role"]["id"], self.app)
        self.assertEqual(urls["role"]["version"], self.ver)

        # Paths are mapped to URLs
        self.assertTrue(urls["shared"]["js"].startswith(base + "/"))
        self.assertTrue(urls["vendor"].startswith(base + "/vendor"))

        # Root always ends with '/'
        self.assertEqual(urls["root"], base.rstrip("/") + "/")

    def test_urls_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            self.cdn_urls({}, "https://cdn.example.com")
        with self.assertRaises(ValueError):
            self.cdn_urls("nope", "https://cdn.example.com")  # type: ignore[arg-type]

    # ---- cdn_dirs ----
    def test_dirs_collects_all_abs_dirs_sorted_unique(self):
        dirs = self.cdn_dirs(self.tree)
        self.assertIn(os.path.join(self.root, "_shared", "css"), dirs)
        self.assertIn(os.path.join(self.root, "roles", self.app, self.ver, "img"), dirs)
        self.assertEqual(dirs, sorted(dirs))
        self.assertEqual(len(dirs), len(set(dirs)))


if __name__ == "__main__":
    unittest.main()
