#!/usr/bin/env bash
# shellcheck shell=bash
# Auto-format all source files using available tools.
# Missing tools are reported and skipped rather than aborting the run.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

skipped=()
ran=()

# ── ruff (Python formatter + auto-fixer) ─────────────────────────────────────
if command -v ruff &>/dev/null; then
	ruff format .
	ruff check . --fix
	ran+=("ruff")
else
	skipped+=("ruff")
fi

# ── shfmt (shell script formatter) ───────────────────────────────────────────
if command -v shfmt &>/dev/null; then
	shfmt -w scripts
	ran+=("shfmt")
else
	skipped+=("shfmt")
fi

# ── shellcheck (shell script linter with autofix via diff) ───────────────────
if command -v shellcheck &>/dev/null; then
	mapfile -t shellcheck_files < <(find . -type f -name '*.sh' 2>/dev/null | sort)
	if [[ "${#shellcheck_files[@]}" -gt 0 ]]; then
		diff_file="$(mktemp)"
		cleanup() { rm -f "${diff_file}"; }
		trap cleanup EXIT
		set +e
		shellcheck -f diff -x "${shellcheck_files[@]}" >"${diff_file}" 2>/dev/null
		set -e
		if [[ -s "${diff_file}" ]]; then
			printf 'Applying ShellCheck autofixes.\n'
			git apply --whitespace=nowarn "${diff_file}"
		fi
	fi
	ran+=("shellcheck")
else
	skipped+=("shellcheck")
fi

# ── summary ──────────────────────────────────────────────────────────────────
if [[ "${#ran[@]}" -gt 0 ]]; then
	printf 'autoformat: ran %s\n' "$(
		IFS=', '
		echo "${ran[*]}"
	)"
fi
if [[ "${#skipped[@]}" -gt 0 ]]; then
	printf 'autoformat: skipped (not installed) %s\n' "$(
		IFS=', '
		echo "${skipped[*]}"
	)"
fi
