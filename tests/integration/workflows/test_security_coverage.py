import fnmatch
import os
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "security-codeql.yml"

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

# Hidden directories that may contain real source files for CodeQL
SCANNED_HIDDEN_DIRS = {
    ".github",
}

# Mapping: CodeQL language name -> filename patterns
CODEQL_FILENAME_INDICATORS: dict[str, list[str]] = {
    "c-cpp": ["*.c", "*.cc", "*.cpp", "*.cxx", "*.h", "*.hh", "*.hpp", "*.hxx"],
    "csharp": ["*.cs"],
    "go": ["*.go"],
    "java-kotlin": ["*.java", "*.kt", "*.kts"],
    "javascript-typescript": ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs"],
    "python": ["*.py"],
    "ruby": ["*.rb"],
    "rust": ["*.rs"],
    "swift": ["*.swift"],
}

# Mapping: CodeQL language name -> repository-relative path patterns
CODEQL_PATH_INDICATORS: dict[str, list[str]] = {
    "actions": [
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        "action.yml",
        "action.yaml",
    ],
}


def _load_active_languages() -> set[str]:
    with open(SECURITY_WORKFLOW_PATH) as fh:
        data = yaml.safe_load(fh)

    include = data["jobs"]["analyze"]["strategy"]["matrix"]["include"]
    return {
        entry["language"]
        for entry in include
        if isinstance(entry, dict) and "language" in entry
    }


def _matching_languages(rel_file: str, filename: str) -> set[str]:
    matched = {
        language
        for language, patterns in CODEQL_FILENAME_INDICATORS.items()
        if any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)
    }
    matched.update(
        language
        for language, patterns in CODEQL_PATH_INDICATORS.items()
        if any(fnmatch.fnmatch(rel_file, pattern) for pattern in patterns)
    )
    return matched


class TestSecurityWorkflowCoverage(unittest.TestCase):
    def test_codeql_languages_match_repository_content(self):
        """The CodeQL workflow must only enable languages that are actually
        present in the repository, and it must not miss any detected language."""

        detected_languages: set[str] = set()

        for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
            dirnames[:] = [
                d
                for d in dirnames
                if d not in SKIP_DIRS
                and (not d.startswith(".") or d in SCANNED_HIDDEN_DIRS)
            ]

            rel_dir = os.path.relpath(dirpath, REPO_ROOT)
            rel_dir = "" if rel_dir == "." else rel_dir

            for filename in filenames:
                rel_file = os.path.join(rel_dir, filename) if rel_dir else filename
                detected_languages.update(_matching_languages(rel_file, filename))

        active_languages = _load_active_languages()
        missing_languages = sorted(detected_languages - active_languages)
        extra_languages = sorted(active_languages - detected_languages)

        problems: list[str] = []
        if missing_languages:
            problems.append(
                "Detected languages missing from .github/workflows/security-codeql.yml:"
            )
            problems.extend(f"  - {language}" for language in missing_languages)

        if extra_languages:
            problems.append(
                "Active CodeQL languages without matching repository files:"
            )
            problems.extend(f"  - {language}" for language in extra_languages)

        if problems:
            self.fail(
                "The CodeQL workflow matrix does not match the repository content.\n"
                "Enable missing languages or comment out inactive ones.\n\n"
                + "\n".join(problems)
            )


if __name__ == "__main__":
    unittest.main()
