#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mapfile -t tags < <(REPOSITORY_DIR="${REPOSITORY_DIR:-.}" "${script_dir}/version_tags.sh")

if [[ ${#tags[@]} -eq 0 ]]; then
	exit 0
fi

last_index=$((${#tags[@]} - 1))
printf '%s\n' "${tags[$last_index]}"
