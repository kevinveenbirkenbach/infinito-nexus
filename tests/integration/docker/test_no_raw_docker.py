"""Guard: forbid raw `docker` / `docker compose` / `docker-compose` CLI
invocations in tracked repository files.

The project ships a `container` / `compose` wrapper around the underlying
engine so that swapping Docker for Podman (or another OCI runtime) does
not require a sweep of every role. This test fails when a file calls the
raw CLI in a place that should go through the wrapper.

Three forms are detected:

1. Single-line shell invocations (start of line / after a shell separator)
   like `docker exec ...`, `sudo docker run ...`, `docker compose up`,
   `docker-compose up`.

2. Ansible argv-lists split across lines:

       ansible.builtin.command:
         argv:
           - docker
           - exec
           - "{{ FOO_CONTAINER }}"

3. Inline shell/command scalars like
   `ansible.builtin.shell: "docker exec ..."`.

Suppression
-----------
Use the unified marker grammar (rule key ``raw-docker``) documented at
``docs/contributing/actions/testing/suppression.md``:

* File-level: ``# nocheck: raw-docker`` anywhere in the first 30 lines
  excludes the whole file. Reserve this for places where the wrapper
  is genuinely unavailable (CI workflow files on hosted runners,
  bootstrap scripts that install the wrapper itself).
* Per-line: ``# noqa: raw-docker`` (or ``# nocheck: raw-docker``) on
  the offending line or the line directly above suppresses that single
  finding.

File enumeration and content reading both go through
``utils.cache.files``, so:

* The set of files to scan respects ``.gitignore`` (no other ignore
  lists).
* The full project-tree walk is memoised process-wide via
  ``iter_non_ignored_files``'s ``lru_cache``.
* File contents are memoised via ``read_text``'s ``lru_cache``. Repeat
  runs inside the same process (e.g. a pytest session that re-uses
  imported modules) avoid both the re-walk and the re-read.
"""

from __future__ import annotations

import os
import re
import unittest
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from utils.annotations.suppress import (
    is_suppressed_at,
    is_suppressed_in_head,
)
from utils.cache.base import PROJECT_ROOT
from utils.cache.files import iter_non_ignored_files, read_text


@dataclass(frozen=True)
class Finding:
    file: str
    line_no: int
    line: str
    rule: str
    suggestion: str


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

# YAML-only rules. The line-anchored RULES above cannot see two patterns
# that are extremely common in Ansible task files: argv lists split
# across lines, and inline scalars where docker follows a YAML key. Both
# must use the wrapper. Restrict these rules to .yml/.yaml files to keep
# unrelated text immune.
YAML_SUFFIXES: Tuple[str, ...] = (".yml", ".yaml")

# Multi-line scan: any `argv:` block whose first/any element is the
# bareword `docker`. The intermediate lines (between `argv:` and the
# offending `- docker` item) must each themselves be list items so the
# match cannot jump across unrelated sections. The {0,40} cap keeps the
# search bounded.
RE_ARGV_DOCKER_BLOCK = re.compile(
    r"""argv:[ \t]*\r?\n"""
    r"""(?:[ \t]*-[ \t]+[^\r\n]*\r?\n){0,40}?"""
    r"""(?P<offender>[ \t]*-[ \t]+['"]?docker['"]?[ \t]*\r?\n)""",
)

# Single-line scan: a Jinja/Ansible task key whose scalar value begins
# with `docker <subcommand>`. Matches both quoted and unquoted forms and
# both fully-qualified (`ansible.builtin.shell:`) and short keys.
RE_YAML_KEY_DOCKER_INLINE = re.compile(
    rf"""^\s*(?:-\s*)?(?:ansible\.builtin\.)?(?:shell|command|raw|cmd)\s*:"""
    rf"""\s*['"]?(?:sudo\s+)?(?:/usr/bin/|/bin/|/usr/local/bin/)?docker\s+"""
    rf"""(?:{"|".join(map(re.escape, _DOCKER_SUBCOMMANDS))})\b""",
    re.IGNORECASE,
)


def _line_no_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _scan_yaml_argv_and_inline(text: str, rel: str) -> List[Finding]:
    findings: List[Finding] = []

    for match in RE_ARGV_DOCKER_BLOCK.finditer(text):
        offender_line_offset = match.start("offender")
        offender_text = match.group("offender").rstrip("\r\n")
        findings.append(
            Finding(
                file=rel,
                line_no=_line_no_at(text, offender_line_offset),
                line=offender_text,
                rule="docker argv list-item",
                suggestion=(
                    "Use 'container' as the first argv element (or rewrite as "
                    "'container <cmd> ...' shell scalar) so the engine stays "
                    "swappable."
                ),
            )
        )

    for idx, line in enumerate(text.splitlines(), start=1):
        if RE_YAML_KEY_DOCKER_INLINE.search(line):
            findings.append(
                Finding(
                    file=rel,
                    line_no=idx,
                    line=line.rstrip("\n"),
                    rule="docker inline scalar",
                    suggestion=(
                        "Replace the leading 'docker <cmd>' with 'container "
                        "<cmd>' in this shell/command scalar."
                    ),
                )
            )

    return findings


def scan_text(text: str, rel: str) -> List[Finding]:
    """Apply every rule to `text`. `rel` is the project-relative POSIX
    path used for diagnostic messages and YAML-rule gating."""
    findings: List[Finding] = []
    seen_offenders = set()  # line_no — dedupe across single+multi-line passes

    for idx, line in enumerate(text.splitlines(), start=1):
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
                seen_offenders.add(idx)
                break

    if rel.endswith(YAML_SUFFIXES):
        for finding in _scan_yaml_argv_and_inline(text, rel):
            if finding.line_no in seen_offenders:
                continue
            findings.append(finding)
            seen_offenders.add(finding.line_no)

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


# Files that can legitimately contain raw `docker` commands. The wrapper
# convention only applies to executable / templated content where the
# wrapper is reachable: Ansible playbooks/roles (.yml, .yaml, .j2) and
# shell scripts (.sh). Documentation (.md), Python source, JSON config,
# and CI workflow files (which run on managed runners without the
# wrapper) are out of scope.
SCAN_EXTENSIONS: Tuple[str, ...] = (".yml", ".yaml", ".j2", ".sh")

# Rule key under the unified suppression grammar. See
# docs/contributing/actions/testing/suppression.md. File-level head
# scans cover the first 30 lines (matches the catalog default).
SUPPRESS_RULE: str = "raw-docker"
HEAD_SCAN_LINES: int = 30


class TestNoRawDockerCommands(unittest.TestCase):
    def test_no_raw_docker_commands_in_repo(self) -> None:
        findings: List[Finding] = []
        project_root_str = str(PROJECT_ROOT)
        for path in iter_non_ignored_files(extensions=SCAN_EXTENSIONS):
            try:
                text = read_text(path)
            except (OSError, UnicodeDecodeError):
                continue
            lines = text.splitlines()
            if is_suppressed_in_head(lines, SUPPRESS_RULE, scan_lines=HEAD_SCAN_LINES):
                continue
            rel = os.path.relpath(path, project_root_str).replace(os.sep, "/")
            for finding in scan_text(text, rel):
                if is_suppressed_at(
                    lines, finding.line_no, SUPPRESS_RULE, mode="same-or-above"
                ):
                    continue
                findings.append(finding)

        if findings:
            self.fail(format_findings(findings))


if __name__ == "__main__":
    unittest.main()
