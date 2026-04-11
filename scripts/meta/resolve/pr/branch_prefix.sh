#!/usr/bin/env bash
set -euo pipefail

: "${PR_HEAD_REF:?Missing PR_HEAD_REF}"
: "${PR_SCOPE:?Missing PR_SCOPE}"

matches_expected_prefix() {
	local head_ref="$1"
	shift

	local prefix
	for prefix in "$@"; do
		case "${head_ref}" in
		"${prefix}" | "${prefix}"/*)
			return 0
			;;
		esac
	done

	return 1
}

case "${PR_SCOPE}" in
agents)
	expected_prefixes=(agent)
	;;
documentation)
	expected_prefixes=(documentation)
	;;
full)
	expected_prefixes=(feature fix update dependabot)
	;;
*)
	echo "ERROR: Unsupported PR_SCOPE '${PR_SCOPE}'." >&2
	exit 1
	;;
esac

branch_prefix="${PR_HEAD_REF%%/*}"

if matches_expected_prefix "${PR_HEAD_REF}" "${expected_prefixes[@]}"; then
	echo "Validated branch prefix '${branch_prefix}' for scope '${PR_SCOPE}' (${expected_prefixes[*]})."
	exit 0
fi

echo "ERROR: Branch '${PR_HEAD_REF}' does not match scope '${PR_SCOPE}'. Expected one of: ${expected_prefixes[*]}." >&2
exit 1
