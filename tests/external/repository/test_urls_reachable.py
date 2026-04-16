"""Check literal HTTP(S) URLs in repository files.

Scans git-tracked and untracked-but-not-ignored text files for literal
``http://`` and ``https://`` URLs. Placeholder/template URLs and reserved
local/example hosts are skipped.

This is an external test because it performs live HTTP requests against the
referenced third-party URLs. HTTP ``401`` (Unauthorized), ``403`` (Forbidden),
and ``405`` (Method Not Allowed) are treated as reachable (server is alive but
auth-gated or method-restricted). HTTP ``418`` (I'm a teapot), ``429`` (Too
Many Requests), ``451`` (Unavailable For Legal Reasons), every ``5xx`` server
response, plus timeouts and connection errors (reset, aborted) emit warning
annotations rather than failing the test — these signal an upstream issue
outside this repository's control. All other ``4xx`` codes fail the test.
"""

from __future__ import annotations

import concurrent.futures
import fnmatch
import ipaddress
import re
import subprocess
import unittest
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlsplit, urlunsplit

import requests

from utils.annotations.message import error, warning

_REPO_ROOT = Path(__file__).resolve().parents[3]
_URL_RE = re.compile(r"https?://[^\s<>'\"`\]]+")
_TEMPLATE_MARKERS = ("${", "{{", "}}", "{%", "%}")
# Lines that contain any of these strings are excluded from URL probing.
# Use this for CDN roots, API base URLs, and other entries that are valid
# application configuration values but return 4xx when probed without a path.
_NOCHECK_MARKERS = ("# nocheck: url", "{# nocheck: url #}", "<!-- nocheck: url -->")
_PUBLIC_HOST_RE = re.compile(r"^[A-Za-z0-9.-]+$")
_RESERVED_HOSTS = {
    "example",
    "example.com",
    "example.net",
    "example.org",
    "localhost",
    "domain-example.com",
}
_RESERVED_HOST_SUFFIXES = (
    ".example",
    ".example.com",
    ".example.net",
    ".example.org",
    ".invalid",
    ".local",
    ".localhost",
    ".localdomain",
    ".test",
    ".tld",
)
# Codes that mean the server responded but access is auth-gated or method-gated.
# These are not dead links; treat them as reachable.
_OK_STATUS_CODES = {
    401,  # Unauthorized: credentials required, server is alive.
    403,  # Forbidden: server is alive, resource intentionally gated.
    405,  # Method Not Allowed: server is alive, HEAD/GET rejected by design.
}
# 4xx codes that mean the server is alive but the resource is not reliably
# probeable. Emit a warning annotation instead of failing the test. All 5xx
# responses are treated as warnings unconditionally (see _probe), since they
# signal an upstream-side problem rather than a stale link in this repo.
_WARNING_STATUS_CODES = {
    418,  # I'm a teapot: playful/custom response; server is alive.
    429,  # Too Many Requests: client rate-limited, transient.
    451,  # Unavailable For Legal Reasons: jurisdiction-specific block.
}
_REQUEST_TIMEOUT_SECONDS = 10
_MAX_WORKERS = 8
_USER_AGENT = "infinito-nexus-url-reachability-check"


class UrlOccurrence(NamedTuple):
    file: Path
    line: int
    url: str


class ProbeOutcome(NamedTuple):
    kind: str
    detail: str


class IgnoreRule(NamedTuple):
    base_dir: Path
    pattern: str
    negated: bool
    directory_only: bool


def _repo_files(root: Path) -> list[Path]:
    """Return git-tracked and untracked-but-not-ignored files."""
    try:
        out = subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            stderr=subprocess.STDOUT,
        )
    except Exception:  # pragma: no cover - git is expected in tests
        return _repo_files_without_git_metadata(root)

    rel_paths = [p for p in out.decode("utf-8", errors="replace").split("\0") if p]
    return sorted((root / rel for rel in rel_paths if (root / rel).is_file()))


def _load_ignore_rules(root: Path) -> list[IgnoreRule]:
    """Load simple .gitignore rules for fallback scans without .git metadata."""
    rules: list[IgnoreRule] = []
    for ignore_file in sorted(root.rglob(".gitignore")):
        base_dir = ignore_file.parent
        try:
            lines = ignore_file.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except OSError:
            continue
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            negated = line.startswith("!")
            if negated:
                line = line[1:]
            directory_only = line.endswith("/")
            pattern = line.rstrip("/")
            if not pattern:
                continue
            rules.append(
                IgnoreRule(
                    base_dir=base_dir,
                    pattern=pattern,
                    negated=negated,
                    directory_only=directory_only,
                )
            )
    return rules


def _match_ignore_rule(rule: IgnoreRule, path: Path) -> bool:
    """Best-effort matcher for the project's current .gitignore patterns."""
    try:
        rel_to_base = path.relative_to(rule.base_dir).as_posix()
    except ValueError:
        return False

    parts = [part for part in rel_to_base.split("/") if part]
    if not parts:
        return False

    pattern = rule.pattern.lstrip("/")
    if rule.directory_only:
        if "/" in pattern:
            return rel_to_base == pattern or rel_to_base.startswith(f"{pattern}/")
        return any(fnmatch.fnmatchcase(part, pattern) for part in parts[:-1])

    if "/" in pattern:
        return fnmatch.fnmatchcase(rel_to_base, pattern)
    return any(fnmatch.fnmatchcase(part, pattern) for part in parts)


def _is_ignored(path: Path, rules: list[IgnoreRule]) -> bool:
    """Return True when *path* matches the loaded fallback .gitignore rules."""
    ignored = False
    for rule in rules:
        if _match_ignore_rule(rule, path):
            ignored = not rule.negated
    return ignored


def _repo_files_without_git_metadata(root: Path) -> list[Path]:
    """Fallback scan for environments where the checkout omits .git metadata."""
    rules = _load_ignore_rules(root)
    files: list[Path] = []
    for path in root.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        if _is_ignored(path, rules):
            continue
        files.append(path)
    return sorted(files)


def _is_probably_text_file(path: Path) -> bool:
    """Skip binary files so the scan stays fast and relevant."""
    try:
        with path.open("rb") as handle:
            sample = handle.read(4096)
    except OSError:
        return False
    return b"\0" not in sample


def _strip_unbalanced_suffix(url: str, opener: str, closer: str) -> str:
    """Trim a trailing closer that belongs to surrounding markup, not the URL."""
    while url.endswith(closer) and url.count(opener) < url.count(closer):
        url = url[:-1]
    return url


def _truncate_at_second_scheme(url: str) -> str:
    """Cut off concatenated URLs like ``foo:https://bar`` after the first URL."""
    positions = [
        pos for pos in (url.find("http://", 1), url.find("https://", 1)) if pos >= 0
    ]
    if not positions:
        return url
    return url[: min(positions)].rstrip(",:")


def _truncate_at_markup_boundary(url: str) -> str:
    """Stop at the first unmatched markdown/prose closer after the URL."""
    result: list[str] = []
    paren_depth = 0
    for char in url:
        if char == ")":
            if paren_depth == 0:
                break
            paren_depth -= 1
        elif char == "]":
            break
        elif char == "(":
            paren_depth += 1
        result.append(char)
    return "".join(result)


def _normalize_url(raw: str) -> str:
    """Trim common trailing punctuation added by prose or markup."""
    url = _truncate_at_second_scheme(raw)
    url = _truncate_at_markup_boundary(url)
    url = url.rstrip(".,;:")
    for escaped in (r"\n", r"\r"):
        while url.endswith(escaped):
            url = url[: -len(escaped)]
    for opener, closer in (("(", ")"), ("[", "]"), ("{", "}")):
        url = _strip_unbalanced_suffix(url, opener, closer)
    return url


def _is_live_literal_url(url: str) -> bool:
    """Return True when *url* is a literal public HTTP(S) URL worth probing."""
    if "…" in url:
        return False
    if any(marker in url for marker in _TEMPLATE_MARKERS):
        return False
    if any(char in url for char in "{}$"):
        return False

    try:
        parsed = urlsplit(url)
    except ValueError:
        return False

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if "." not in host:
        return False
    if not _PUBLIC_HOST_RE.match(host):
        return False
    if host.split(".", 1)[0] == "example":
        return False
    if host in _RESERVED_HOSTS:
        return False
    if any(host.endswith(suffix) for suffix in _RESERVED_HOST_SUFFIXES):
        return False

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True

    return not (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_private
        or ip.is_reserved
        or ip.is_unspecified
    )


def _extract_urls(path: Path) -> list[UrlOccurrence]:
    """Return URL occurrences from *path* that should be probed live."""
    if not _is_probably_text_file(path):
        return []

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    occurrences: list[UrlOccurrence] = []
    for line_no, line in enumerate(lines, start=1):
        prev_line = lines[line_no - 2] if line_no >= 2 else ""
        if any(marker in line or marker in prev_line for marker in _NOCHECK_MARKERS):
            continue
        for match in _URL_RE.finditer(line):
            url = _normalize_url(match.group(0))
            if _is_live_literal_url(url):
                occurrences.append(UrlOccurrence(path, line_no, url))
    return occurrences


def _probe_key(url: str) -> str:
    """Deduplicate URLs by dropping fragments, which do not affect HTTP reachability."""
    parsed = urlsplit(url)
    return urlunsplit(parsed._replace(fragment=""))


def _probe_url(url: str) -> ProbeOutcome:
    """Probe one URL and classify the result for external-test stability."""
    try:
        response = requests.get(
            url,
            allow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
            stream=True,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        try:
            status = response.status_code
        finally:
            response.close()
    except requests.Timeout as exc:
        return ProbeOutcome("warn", f"Timeout: {exc}")
    except requests.ConnectionError as exc:
        return ProbeOutcome("warn", f"ConnectionError: {exc}")
    except requests.RequestException as exc:
        return ProbeOutcome("fail", f"{type(exc).__name__}: {exc}")
    except Exception as exc:  # pragma: no cover - defensive safety net
        return ProbeOutcome("fail", f"{type(exc).__name__}: {exc}")

    if status < 400 or status in _OK_STATUS_CODES:
        return ProbeOutcome("ok", f"HTTP {status}")
    if status in _WARNING_STATUS_CODES or status >= 500:
        return ProbeOutcome("warn", f"HTTP {status}")
    return ProbeOutcome("fail", f"HTTP {status}")


def _collect_occurrences(root: Path) -> dict[str, list[UrlOccurrence]]:
    """Collect probe-worthy URLs from all non-ignored repository files."""
    by_url: dict[str, list[UrlOccurrence]] = defaultdict(list)
    for path in _repo_files(root):
        for occurrence in _extract_urls(path):
            by_url[_probe_key(occurrence.url)].append(occurrence)
    return dict(by_url)


class TestUrlsReachable(unittest.TestCase):
    """Literal public HTTP(S) URLs in repository files should stay reachable."""

    def test_public_http_urls_are_reachable(self) -> None:
        occurrences_by_url = _collect_occurrences(_REPO_ROOT)
        self.assertTrue(
            occurrences_by_url,
            "No probe-worthy public HTTP(S) URLs found in repository files.",
        )

        failing_found: list[tuple[str, UrlOccurrence, str, int]] = []
        warnings_found: list[tuple[str, UrlOccurrence, str, int]] = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=_MAX_WORKERS
        ) as executor:
            future_to_url = {
                executor.submit(_probe_url, url): url
                for url in sorted(occurrences_by_url)
            }
            for future in concurrent.futures.as_completed(future_to_url):
                probe_url = future_to_url[future]
                outcome = future.result()
                occurrences = occurrences_by_url[probe_url]

                if outcome.kind == "fail":
                    failing_found.append(
                        (
                            "External URL failure",
                            occurrences[0],
                            f"{probe_url} -> {outcome.detail}",
                            len(occurrences),
                        )
                    )
                    continue

                if outcome.kind == "warn":
                    warnings_found.append(
                        (
                            "External URL reachability",
                            occurrences[0],
                            f"{probe_url} -> {outcome.detail}",
                            len(occurrences),
                        )
                    )

        for title, occurrence, message, count in sorted(
            failing_found,
            key=lambda item: (item[1].file.as_posix(), item[1].line, item[2]),
        ):
            rel = occurrence.file.relative_to(_REPO_ROOT).as_posix()
            suffix = "" if count == 1 else f" ({count} occurrences)"
            error(
                f"{message}{suffix}",
                title=title,
                file=rel,
                line=occurrence.line,
            )

        for title, occurrence, message, count in sorted(
            warnings_found,
            key=lambda item: (item[1].file.as_posix(), item[1].line, item[2]),
        ):
            rel = occurrence.file.relative_to(_REPO_ROOT).as_posix()
            suffix = "" if count == 1 else f" ({count} occurrences)"
            warning(
                f"{message}{suffix}",
                title=title,
                file=rel,
                line=occurrence.line,
            )

        if not failing_found:
            return

        lines = [
            f"Failing HTTP(S) URLs found ({len(failing_found)}):",
            "",
            "  Fix the URL, remove it, or adjust the reference.",
            "  401/403/405 = server alive (auth/method). 418/429/451 + all 5xx = warning. Other 4xx = fail.",
            "",
        ]
        for _title, occurrence, message, count in sorted(
            failing_found,
            key=lambda item: (item[1].file.as_posix(), item[1].line, item[2]),
        ):
            rel = occurrence.file.relative_to(_REPO_ROOT).as_posix()
            suffix = "" if count == 1 else f" ({count} occurrences)"
            lines.append(f"  {rel}:{occurrence.line}: {message}{suffix}")
        self.fail("\n".join(lines))


if __name__ == "__main__":
    unittest.main()
