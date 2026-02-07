from __future__ import annotations

import os
import re
import subprocess
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class Finding:
    file: str
    line_no: int
    line: str
    rule: str
    suggestion: str


# Whitelist: ignore these file endings / filenames / path fragments
WHITELIST_SUFFIXES: Tuple[str, ...] = (
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
    ".lock",
)

WHITELIST_FILENAMES: Tuple[str, ...] = ("LICENSE",)

WHITELIST_PATH_FRAGMENTS: Tuple[str, ...] = (
    "/.git/",
    "/.venv/",
    "/.mypy_cache/",
    "/.pytest_cache/",
    "/node_modules/",
    "/dist/",
    "/build/",
    ".github/workflows/",
    "/scripts/",
    "/.tox/",
    "/cli/",
    "infinito_nexus.egg-info/",
)

# Optional: allow docker mentions in specific files (keep empty for strict)
WHITELIST_EXACT_PATHS: Tuple[str, ...] = (
    # "docs/somefile.txt",
)

# Only treat "docker ..." as a command when it appears in a command-like context.
# i.e. start of line or after common shell operators / subshell / command substitution.
_CMD_PREFIX = r"""
(?:
    ^\s*                                  # line start
  | [;&(]\s*                               # ; & (
  | \|\s*                                  # pipe
  | &&\s*                                  # &&
  | \|\|\s*                                # ||
  | \$(?:\(|\{)\s*                         # $(  or ${
)
"""

# Optional sudo and optional absolute path to docker binary.
_DOCKER_BIN = r"(?:sudo\s+)?(?:/usr/bin/|/bin/|/usr/local/bin/)?docker"
_DOCKER_COMPOSE_BIN = r"(?:sudo\s+)?(?:/usr/bin/|/bin/|/usr/local/bin/)?docker-compose"

# Allowlist of real docker top-level subcommands that you consider "valid invocations".
# Extend when needed (keep it explicit to avoid false positives).
_DOCKER_SUBCOMMANDS = (
    "run",
    "exec",
    "ps",
    "inspect",
    "logs",
    "pull",
    "push",
    "build",
    "login",
    "logout",
    "tag",
    "rm",
    "rmi",
    "start",
    "stop",
    "restart",
    "kill",
    "cp",
    "info",
    "version",
    "events",
    "stats",
    "system",
    "container",
    "image",
    "volume",
    "network",
    "manifest",
    "buildx",
    "builder",
    "context",
)

# Allowlist of compose verbs (docker compose <verb> / docker-compose <verb>)
_COMPOSE_VERBS = (
    "up",
    "down",
    "pull",
    "push",
    "build",
    "config",
    "ps",
    "logs",
    "exec",
    "run",
    "start",
    "stop",
    "restart",
    "rm",
    "create",
    "images",
    "top",
)

# Compile patterns with VERBOSE for readability.
RE_DOCKER_CMD = re.compile(
    rf"{_CMD_PREFIX}{_DOCKER_BIN}\s+(?:{'|'.join(map(re.escape, _DOCKER_SUBCOMMANDS))})\b",
    re.IGNORECASE | re.VERBOSE,
)

RE_DOCKER_COMPOSE_CMD = re.compile(
    rf"{_CMD_PREFIX}{_DOCKER_BIN}\s+compose\s+(?:{'|'.join(map(re.escape, _COMPOSE_VERBS))})\b",
    re.IGNORECASE | re.VERBOSE,
)

RE_DOCKER_DASH_COMPOSE_CMD = re.compile(
    rf"{_CMD_PREFIX}{_DOCKER_COMPOSE_BIN}\s+(?:{'|'.join(map(re.escape, _COMPOSE_VERBS))})\b",
    re.IGNORECASE | re.VERBOSE,
)

# Rules: order matters (prefer specific messages)
RULES: Tuple[Tuple[str, re.Pattern, str], ...] = (
    (
        "docker compose usage",
        RE_DOCKER_COMPOSE_CMD,
        "Use 'compose <verb> ...' instead of 'docker compose <verb> ...'.",
    ),
    (
        "docker-compose usage",
        RE_DOCKER_DASH_COMPOSE_CMD,
        "Use 'compose <verb> ...' instead of 'docker-compose <verb> ...'.",
    ),
    (
        "docker CLI usage",
        RE_DOCKER_CMD,
        "Use 'container <cmd> ...' instead of calling 'docker <cmd> ...' directly.",
    ),
)


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / ".git").exists():
            return p
    return Path.cwd().resolve()


def git_ls_files(root: Path) -> List[Path]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "-z"],
            stderr=subprocess.STDOUT,
        )
        rels = [p for p in out.decode("utf-8", errors="replace").split("\0") if p]
        return [root / p for p in rels]
    except Exception:
        results: List[Path] = []
        for r, dirs, files in os.walk(root):
            pruned = []
            for d in list(dirs):
                rel = (Path(r) / d).relative_to(root).as_posix()
                if any(fragment in f"/{rel}/" for fragment in WHITELIST_PATH_FRAGMENTS):
                    pruned.append(d)
            for d in pruned:
                dirs.remove(d)

            for f in files:
                results.append(Path(r) / f)
        return results


def is_whitelisted(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()

    if rel in WHITELIST_EXACT_PATHS:
        return True
    if path.name in WHITELIST_FILENAMES:
        return True
    if any(rel.endswith(suf) for suf in WHITELIST_SUFFIXES):
        return True

    rel_wrapped = f"/{rel}/"
    if any(fragment in rel_wrapped for fragment in WHITELIST_PATH_FRAGMENTS):
        return True

    return False


def is_probably_text(data: bytes) -> bool:
    return b"\x00" not in data


def scan_file(path: Path, root: Path) -> List[Finding]:
    findings: List[Finding] = []
    rel = path.relative_to(root).as_posix()

    try:
        raw = path.read_bytes()
    except Exception:
        return findings

    if not is_probably_text(raw):
        return findings

    text = raw.decode("utf-8", errors="replace")
    for idx, line in enumerate(text.splitlines(), start=1):
        # Only flag when it looks like a command invocation.
        for rule_name, pattern, suggestion in RULES:
            if pattern.search(line):
                findings.append(
                    Finding(
                        file=rel,
                        line_no=idx,
                        line=line.rstrip("\n"),
                        rule=rule_name,
                        suggestion=suggestion,
                    )
                )
                break

    return findings


def format_findings(findings: Sequence[Finding]) -> str:
    lines: List[str] = []
    lines.append("Forbidden raw Docker command invocations detected.")
    lines.append("")
    lines.append("Why this matters:")
    lines.append(
        "- We enforce a convenience wrapper ('container' / 'compose') so the container engine can be switched quickly"
    )
    lines.append(
        "  (e.g., Docker -> Podman) without refactoring command strings across the repo."
    )
    lines.append("")
    lines.append("Fix rules:")
    lines.append("- 'docker <cmd> ...'              -> 'container <cmd> ...'")
    lines.append("- 'docker compose <verb> ...'     -> 'compose <verb> ...'")
    lines.append("- 'docker-compose <verb> ...'     -> 'compose <verb> ...'")
    lines.append("")
    lines.append("Findings:")
    for f in findings:
        lines.append(f"- {f.file}:{f.line_no}: {f.line.strip()}")
        lines.append(f"  -> {f.suggestion}")
    return "\n".join(lines)


class TestNoRawDockerCommands(unittest.TestCase):
    def test_no_raw_docker_commands_in_repo(self) -> None:
        root = repo_root()
        files = git_ls_files(root)

        findings: List[Finding] = []
        for p in files:
            if not p.is_file():
                continue
            if is_whitelisted(p, root):
                continue
            findings.extend(scan_file(p, root))

        if findings:
            self.fail(format_findings(findings))


if __name__ == "__main__":
    unittest.main()
