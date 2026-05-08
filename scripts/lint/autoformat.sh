#!/usr/bin/env bash
# shellcheck shell=bash
# Auto-format all source files using available tools.
# Missing tools are reported and skipped rather than aborting the run.
#
# Per-tool workers run concurrently by default. Set PARALLEL=0 (also
# accepts `false`/`no`/`off`) to fall back to sequential execution.
# Tools that touch the same files are kept on the same worker (the
# shfmt+shellcheck pair both writes to scripts/*.sh, so they share a
# worker) regardless of the parallelism setting.

set -euo pipefail

# Default: parallel. Override with `PARALLEL=0` for sequential.
PARALLEL="${PARALLEL:-true}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

status_dir="$(mktemp -d)"
trap 'rm -rf "${status_dir}"' EXIT

write_status() {
	# $1 = tool name, $2 = OK|SKIP
	printf '%s %s\n' "$2" "$1" >"${status_dir}/$1"
}

# ── individual workers ───────────────────────────────────────────────────────

run_ruff() {
	if command -v ruff &>/dev/null; then
		ruff format .
		ruff check . --fix
		write_status ruff OK
	else
		write_status ruff SKIP
	fi
}

run_sort_claude_settings() {
	if command -v python3 &>/dev/null; then
		bash "${SCRIPT_DIR}/sort_claude_settings.sh"
		write_status sort-claude-settings OK
	else
		write_status sort-claude-settings SKIP
	fi
}

# shfmt + shellcheck both write to scripts/*.sh and therefore share a
# worker. They run sequentially within this function so their edits do
# not race.
run_shell_pair() {
	if command -v shfmt &>/dev/null; then
		shfmt -w scripts
		write_status shfmt OK
	else
		write_status shfmt SKIP
	fi

	if command -v shellcheck &>/dev/null; then
		mapfile -t shellcheck_files < <(find . -type f -name '*.sh' 2>/dev/null | sort)
		if [[ "${#shellcheck_files[@]}" -gt 0 ]]; then
			local diff_file
			diff_file="$(mktemp)"
			set +e
			shellcheck -f diff -x "${shellcheck_files[@]}" >"${diff_file}" 2>/dev/null
			set -e
			if [[ -s "${diff_file}" ]]; then
				printf 'Applying ShellCheck autofixes.\n'
				git apply --whitespace=nowarn "${diff_file}"
			fi
			rm -f "${diff_file}"
		fi
		write_status shellcheck OK
	else
		write_status shellcheck SKIP
	fi
}

run_markdownlint() {
	if command -v markdownlint-cli2 &>/dev/null; then
		markdownlint-cli2 --fix >/dev/null 2>&1 || true
		write_status markdownlint-cli2 OK
	else
		write_status markdownlint-cli2 SKIP
	fi
}

run_ansible_lint() {
	if command -v ansible-lint &>/dev/null; then
		ansible-lint --fix >/dev/null 2>&1 || true
		write_status ansible-lint OK
	else
		write_status ansible-lint SKIP
	fi
}

run_mbake() {
	if command -v mbake &>/dev/null; then
		mbake format Makefile >/dev/null 2>&1 || true
		mbake format Makefile >/dev/null 2>&1 || true
		write_status mbake OK
	else
		write_status mbake SKIP
	fi
}

# ── dispatch ─────────────────────────────────────────────────────────────────

is_truthy() {
	case "${1:-}" in
	1 | true | TRUE | True | yes | YES | Yes | on | ON | On) return 0 ;;
	*) return 1 ;;
	esac
}

workers=(run_ruff run_sort_claude_settings run_shell_pair run_markdownlint run_ansible_lint run_mbake)

if is_truthy "${PARALLEL}"; then
	for w in "${workers[@]}"; do "${w}" & done
	wait
else
	for w in "${workers[@]}"; do "${w}"; done
fi

# ── summary ──────────────────────────────────────────────────────────────────

ran=()
skipped=()
for f in "${status_dir}"/*; do
	[[ -f "${f}" ]] || continue
	line="$(<"${f}")"
	case "${line}" in
	OK\ *) ran+=("${line#OK }") ;;
	SKIP\ *) skipped+=("${line#SKIP }") ;;
	esac
done

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
