#!/usr/bin/env bash
# shellcheck shell=bash
#
# Run galaxy-importer against every roles/<role>/ directory. Galaxy-importer
# is the official tool Ansible Galaxy uses to validate role uploads, so it
# enforces the strict Galaxy schema (allowed platforms, required fields,
# galaxy_tags shape, etc.).
#
# Any role that fails galaxy-importer's schema validation breaks the lint.
# The canonical `galaxy_info.company` block-scalar is kept intentionally
# short (`Kevin Veen-Birkenbach\nhttps://www.veen.world`, 45 chars) so it
# stays under Galaxy's hard 50-character limit and this tool can run as a
# strict gate.
#
# Per-role output is captured in /tmp/galaxy-importer-<role>.log so
# failures point straight at the offending file.
#
# Per-role workers run concurrently by default. Set PARALLEL=0 (also
# accepts `false`/`no`/`off`) to fall back to sequential execution.

set -euo pipefail

# Default: parallel. Override with `PARALLEL=0` for sequential.
PARALLEL="${PARALLEL:-true}"

# Internal knob — change here when needed; not exposed as env var.
NAMESPACE="infinito"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

if ! python3 -c 'import galaxy_importer' >/dev/null 2>&1; then
	echo "galaxy-importer not installed. Run 'make install-lint' first." >&2
	exit 127
fi

log_dir="${TMPDIR:-/tmp}"

is_truthy() {
	case "${1:-}" in
	1 | true | TRUE | True | yes | YES | Yes | on | ON | On) return 0 ;;
	*) return 1 ;;
	esac
}

if is_truthy "${PARALLEL}"; then
	xargs_workers="$(nproc 2>/dev/null || echo 4)"
else
	xargs_workers=1
fi

# Skip top-level dotfile directories under roles/ (e.g. `.claude/`), which
# are tooling artefacts, not Ansible roles.
mapfile -t role_names < <(
	find roles -mindepth 1 -maxdepth 1 -type d ! -name '.*' \
		-printf '%f\n' | sort
)
total=${#role_names[@]}

echo "galaxy-importer: linting ${total} role(s) with parallelism=${xargs_workers}"

# Each subshell prints `OK <name>` or `FAIL <name>` to stdout. We collect
# both for a final summary; the per-role full output lives in the log file.
#
# Treat-as-success rule: galaxy-importer rejects bare role names in
# `meta/main.yml.dependencies` (it expects collection-style
# `namespace.name`). We use bare names because Ansible resolves them via
# the role-path at runtime, not via collections. A run whose ONLY error
# is the namespace-format check is therefore considered a pass; any other
# error (description length, missing readme, schema violation, ...) still
# fails.
results_file="$(mktemp)"
trap 'rm -f "${results_file}"' EXIT

# shellcheck disable=SC2016 # single quotes are intentional: vars are expanded by the inner bash -c, not the outer shell
printf '%s\n' "${role_names[@]}" | xargs -n1 -P "${xargs_workers}" -I{} bash -c '
	name="$1"
	log="$2/galaxy-importer-${name}.log"
	if (cd roles && python3 -m galaxy_importer.main \
			--legacy-role "${name}" \
			--namespace "$3" \
			>"${log}" 2>&1); then
		printf "OK   %s\n" "${name}"
		exit 0
	fi
	# galaxy-importer failed; check if every ERROR line is the
	# bare-name dependency complaint we accept.
	if [[ "$(grep -c "^ERROR" "${log}")" -gt 0 ]] \
		&& [[ "$(grep -E "^ERROR" "${log}" \
			| grep -vE "must have namespace and name separated by .\\..$" \
			| wc -l)" -eq 0 ]]; then
		printf "OK   %s  (dep-namespace warning ignored)\n" "${name}"
		exit 0
	fi
	printf "FAIL %s\n" "${name}"
' _ {} "${log_dir}" "${NAMESPACE}" |
	tee "${results_file}"

failures=$(grep -c '^FAIL ' "${results_file}" || true)
checked=$(wc -l <"${results_file}")
echo
echo "galaxy-importer: ${checked} role(s) checked, ${failures} failed"
if [[ "${failures}" -gt 0 ]]; then
	echo "  → see /tmp/galaxy-importer-<role>.log for per-role detail."
fi
if [[ "${failures}" -gt 0 ]]; then
	exit 1
fi
exit 0
