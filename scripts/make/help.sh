#!/usr/bin/env bash
# Print every Make target with its description.
#
# Descriptions are taken from the comment line(s) directly above each
# target in the Makefile. Consecutive comment lines are joined with a
# space. Blank lines, recipe bodies, variable assignments, .PHONY
# blocks and other directives are ignored.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MAKEFILE="${REPO_ROOT}/Makefile"

if [[ ! -f "${MAKEFILE}" ]]; then
	echo "make help: Makefile not found at ${MAKEFILE}" >&2
	exit 1
fi

if [[ -t 1 ]]; then
	C_BOLD=$'\033[1m'
	C_CYAN=$'\033[36m'
	C_GREEN=$'\033[32m'
	C_DIM=$'\033[2m'
	C_RESET=$'\033[0m'
else
	C_BOLD=""
	C_CYAN=""
	C_GREEN=""
	C_DIM=""
	C_RESET=""
fi

printf '\n%sInfinito.Nexus Make targets%s\n' "${C_BOLD}${C_CYAN}" "${C_RESET}"
printf '%sUsage: make <target>%s\n\n' "${C_DIM}" "${C_RESET}"

awk '
	/^#/ {
		line = $0
		sub(/^#[[:space:]]?/, "", line)
		if (comment == "") {
			comment = line
		} else {
			comment = comment " " line
		}
		next
	}
	/^\.[A-Za-z]/ { comment = ""; next }
	/^[[:space:]]*$/ { comment = ""; next }
	/^[A-Za-z][A-Za-z0-9_.-]*:/ && !/:=/ && !/[?+]=/ {
		target = $0
		sub(/:.*$/, "", target)
		if (!seen[target]++) {
			printf "%s\t%s\n", target, (comment == "" ? "-" : comment)
		}
		comment = ""
		next
	}
	/^[[:space:]]/ { next }
	{ comment = "" }
' "${MAKEFILE}" |
	sort |
	awk -F'\t' -v g="${C_GREEN}" -v d="${C_DIM}" -v r="${C_RESET}" '
		{ printf "  %s%-32s%s %s%s%s\n", g, $1, r, d, $2, r }
	'

printf '\n'

if command -v infinito >/dev/null 2>&1; then
	printf '%sFor deployment & CLI help, run:%s\n' "${C_BOLD}" "${C_RESET}"
	printf '  %sinfinito --help%s\n\n' "${C_GREEN}" "${C_RESET}"
else
	printf '%sFor deployment & CLI help, run:%s\n' "${C_BOLD}" "${C_RESET}"
	printf '  %spython -m cli --help%s\n' "${C_GREEN}" "${C_RESET}"
	# shellcheck disable=SC2016 # backticks are literal hint text, not command substitution
	printf '  %s(Install the `infinito` console script via `make install-python-dev` to use `infinito --help` instead.)%s\n\n' "${C_DIM}" "${C_RESET}"
fi

printf '%sDocumentation:%s %s%s\n\n' "${C_BOLD}" "${C_RESET}" "${C_CYAN}https://docs.infinito.nexus${C_RESET}" ""
