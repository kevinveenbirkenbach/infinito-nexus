import fnmatch
import os
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPENDABOT_PATH = REPO_ROOT / ".github" / "dependabot.yml"

# Directories skipped when walking the repository
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".tox",
    "build",
    "dist",
}

# Hidden directories that may contain real dependency manifests
SCANNED_HIDDEN_DIRS = {
    ".github",
    ".devcontainer",
}

# File suffixes that indicate generated/template files, not real dependency files
SKIP_SUFFIXES = (".j2",)

# Mapping: Dependabot ecosystem name → indicator filename patterns (fnmatch-style)
ECOSYSTEM_FILENAME_INDICATORS: dict[str, list[str]] = {
    "pip": [
        "pyproject.toml",
        "requirements.txt",
        "requirements*.txt",
        "setup.py",
        "setup.cfg",
        "Pipfile",
    ],
    "uv": ["uv.lock"],
    "npm": ["package.json"],
    "bun": ["bun.lockb"],
    "cargo": ["Cargo.toml"],
    "rust-toolchain": ["rust-toolchain.toml", "rust-toolchain"],
    "composer": ["composer.json"],
    "gomod": ["go.mod"],
    "maven": ["pom.xml"],
    "gradle": ["build.gradle", "build.gradle.kts"],
    "nuget": ["*.csproj", "*.fsproj", "*.vbproj"],
    "dotnet-sdk": ["global.json"],
    "mix": ["mix.exs"],
    "swift": ["Package.swift"],
    "pub": ["pubspec.yaml"],
    "conda": ["environment.yml"],
    "julia": ["Project.toml", "JuliaProject.toml"],
    "elm": ["elm.json"],
    "bazel": ["MODULE.bazel", "WORKSPACE", "WORKSPACE.bazel"],
    "vcpkg": ["vcpkg.json"],
    "gitsubmodule": [".gitmodules"],
    "bundler": ["Gemfile", "gems.rb"],
    "terraform": ["*.tf"],
    "opentofu": ["*.tf"],
    "helm": ["Chart.yaml"],
    "pre-commit": [".pre-commit-config.yaml"],
    "docker": ["Dockerfile", "*.dockerfile", "Dockerfile.*"],
    "docker-compose": [
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
    ],
}

# Mapping: Dependabot ecosystem name → repository-relative path patterns
ECOSYSTEM_PATH_INDICATORS: dict[str, list[str]] = {
    "github-actions": [
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        "action.yml",
        "action.yaml",
    ],
    "devcontainers": [
        ".devcontainer/devcontainer.json",
        ".devcontainer/*/devcontainer.json",
    ],
}

# Ecosystem groups where any one active member covers the shared file type.
# E.g. terraform and opentofu both consume *.tf — either being active is sufficient.
EQUIVALENT_ECOSYSTEMS: list[frozenset[str]] = [
    frozenset({"terraform", "opentofu"}),
]


def _dir_covers(dep_dir: str, file_rel_dir: str) -> bool:
    """Return True if a Dependabot directory pattern covers a file's relative directory.

    dep_dir is as written in dependabot.yml (e.g. '/', '/**', '/roles/foo/').
    file_rel_dir is the directory of the file relative to REPO_ROOT (e.g. 'roles/foo').
    An empty file_rel_dir means the file is at the repo root.

    For many ecosystems GitHub's Dependabot treats '/' as "search recursively
    from root", which means it covers all sub-directories too.
    """
    norm_dep = "/" + dep_dir.strip("/") if dep_dir.strip("/") else "/"
    norm_file = "/" + file_rel_dir.strip("/") if file_rel_dir else "/"

    # '/' and '/**' are both "cover the entire repository"
    if norm_dep in ("/", "/**"):
        return True

    return norm_file == norm_dep or norm_file.startswith(norm_dep + "/")


def _load_active_entries() -> list[dict]:
    with open(DEPENDABOT_PATH) as fh:
        data = yaml.safe_load(fh)
    return data.get("updates", [])


def _get_entry_dirs(entry: dict) -> list[str]:
    if "directories" in entry:
        return entry["directories"]
    return [entry.get("directory", "/")]


def _matching_ecosystems(rel_file: str, filename: str) -> set[str]:
    matched = {
        ecosystem
        for ecosystem, patterns in ECOSYSTEM_FILENAME_INDICATORS.items()
        if any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)
    }
    matched.update(
        ecosystem
        for ecosystem, patterns in ECOSYSTEM_PATH_INDICATORS.items()
        if any(fnmatch.fnmatch(rel_file, pattern) for pattern in patterns)
    )
    return matched


class TestDependabotCoverage(unittest.TestCase):
    def test_all_dependency_files_are_covered(self):
        """Every dependency file found in the repository must be covered by an
        active Dependabot entry.  The test fails when a new ecosystem file is
        added (e.g. a Gemfile or Cargo.toml inside a role) but the matching
        ecosystem is still commented-out in .github/dependabot.yml."""

        active = _load_active_entries()

        # Build lookup: ecosystem → [directory patterns]
        ecosystem_dirs: dict[str, list[str]] = {}
        for entry in active:
            eco = entry["package-ecosystem"]
            ecosystem_dirs.setdefault(eco, []).extend(_get_entry_dirs(entry))

        uncovered: list[str] = []

        for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
            # Prune directories we never want to scan
            dirnames[:] = [
                d
                for d in dirnames
                if d not in SKIP_DIRS
                and (not d.startswith(".") or d in SCANNED_HIDDEN_DIRS)
            ]

            rel_dir = os.path.relpath(dirpath, REPO_ROOT)
            rel_dir = "" if rel_dir == "." else rel_dir

            for filename in filenames:
                # Skip Jinja2 templates and other generated files
                if any(filename.endswith(s) for s in SKIP_SUFFIXES):
                    continue

                rel_file = os.path.join(rel_dir, filename) if rel_dir else filename

                for ecosystem in sorted(_matching_ecosystems(rel_file, filename)):
                    # Collect all ecosystem names that are equivalent for this file
                    candidates: set[str] = {ecosystem}
                    for group in EQUIVALENT_ECOSYSTEMS:
                        if ecosystem in group:
                            candidates |= group

                    covered = any(
                        any(
                            _dir_covers(dep_dir, rel_dir)
                            for dep_dir in ecosystem_dirs.get(eco, [])
                        )
                        for eco in candidates
                    )

                    if not covered:
                        uncovered.append(f"{rel_file}  →  ecosystem: {ecosystem}")

        if uncovered:
            self.fail(
                "The following dependency files exist but are NOT covered by an active"
                " Dependabot entry in .github/dependabot.yml.\n"
                "Enable the matching ecosystem or add the directory to an existing entry:\n\n"
                + "\n".join(f"  {entry}" for entry in sorted(uncovered))
            )


if __name__ == "__main__":
    unittest.main()
