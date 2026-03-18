#!/usr/bin/env bash
# shellcheck shell=bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

run_privileged() {
	if [[ "${EUID}" -eq 0 ]] || ! command -v sudo >/dev/null 2>&1; then
		"$@"
	else
		sudo "$@"
	fi
}

log() {
	printf '%s\n' "$*"
}

warn() {
	printf '%s\n' "$*" >&2
}

detect_package_manager() {
	if command -v pacman >/dev/null 2>&1; then
		printf 'pacman\n'
	elif command -v apt-get >/dev/null 2>&1; then
		printf 'apt-get\n'
	elif command -v dnf >/dev/null 2>&1; then
		printf 'dnf\n'
	elif command -v yum >/dev/null 2>&1; then
		printf 'yum\n'
	elif command -v brew >/dev/null 2>&1; then
		printf 'brew\n'
	else
		return 1
	fi
}

install_package_candidates() {
	local manager="$1"
	shift
	local package

	case "${manager}" in
	apt-get)
		run_privileged apt-get update
		;;
	dnf)
		run_privileged dnf -y install dnf-plugins-core || true
		run_privileged dnf -y install epel-release || true
		;;
	yum)
		run_privileged yum -y install yum-utils || true
		run_privileged yum -y install epel-release || true
		;;
	esac

	for package in "$@"; do
		log "Installing package '${package}' via ${manager}"
		case "${manager}" in
		pacman)
			if run_privileged pacman -Syu --noconfirm --needed "${package}"; then
				return 0
			fi
			;;
		apt-get)
			if run_privileged apt-get install -y --no-install-recommends "${package}"; then
				return 0
			fi
			;;
		dnf)
			if run_privileged dnf -y install "${package}"; then
				return 0
			fi
			;;
		yum)
			if run_privileged yum -y install "${package}"; then
				return 0
			fi
			;;
		brew)
			if brew install "${package}"; then
				return 0
			fi
			;;
		*)
			warn "Unsupported package manager: ${manager}"
			return 1
			;;
		esac
	done

	return 1
}

install_command() {
	local manager="$1"
	local command_name="$2"

	case "${command_name}:${manager}" in
	actionlint:pacman | actionlint:apt-get | actionlint:dnf | actionlint:yum | actionlint:brew)
		install_package_candidates "${manager}" actionlint
		;;
	ansible-galaxy:pacman | ansible-galaxy:apt-get | ansible-galaxy:dnf | ansible-galaxy:yum | ansible-galaxy:brew | \
		ansible-playbook:pacman | ansible-playbook:apt-get | ansible-playbook:dnf | ansible-playbook:yum | ansible-playbook:brew)
		if [[ "${manager}" == "brew" ]]; then
			install_package_candidates "${manager}" ansible
		else
			install_package_candidates "${manager}" ansible-core ansible
		fi
		;;
	ruff:pacman | ruff:apt-get | ruff:dnf | ruff:yum | ruff:brew)
		install_package_candidates "${manager}" ruff
		;;
	shfmt:pacman | shfmt:apt-get | shfmt:dnf | shfmt:yum | shfmt:brew)
		install_package_candidates "${manager}" shfmt
		;;
	shellcheck:pacman | shellcheck:apt-get | shellcheck:dnf | shellcheck:yum | shellcheck:brew)
		install_package_candidates "${manager}" shellcheck
		;;
	*)
		warn "No installer mapping defined for '${command_name}' on '${manager}'."
		return 1
		;;
	esac
}

ensure_command() {
	local command_name="$1"

	if command -v "${command_name}" >/dev/null 2>&1; then
		return 0
	fi

	local manager
	manager="$(detect_package_manager)" || {
		warn "No supported package manager found to install '${command_name}'."
		return 1
	}

	log "Missing command '${command_name}'. Attempting installation via ${manager}."
	install_command "${manager}" "${command_name}" || {
		warn "Installation failed for '${command_name}' via ${manager}."
		return 1
	}

	command -v "${command_name}" >/dev/null 2>&1 || {
		warn "Command '${command_name}' is still unavailable after installation."
		return 1
	}
}

ensure_required_ansible_collections() {
	local collections_base_dir="${HOME}/.ansible/collections"
	local collections_dir="${collections_base_dir}/ansible_collections"
	local missing=()
	local max_attempts=5
	local attempt=1
	local sleep_time

	[[ -d "${collections_dir}/community/general" ]] || missing+=(community.general)
	[[ -d "${collections_dir}/hetzner/hcloud" ]] || missing+=(hetzner.hcloud)
	[[ -d "${collections_dir}/kewlfft/aur" ]] || missing+=(kewlfft.aur)

	if [[ "${#missing[@]}" -eq 0 ]]; then
		return 0
	fi

	while true; do
		log "Installing missing Ansible collections: ${missing[*]} (attempt ${attempt}/${max_attempts})"

		if ansible-galaxy collection install \
			-r "${REPO_ROOT}/requirements/requirements.galaxy.yml" \
			-p "${collections_base_dir}" \
			--force-with-deps; then
			return 0
		fi

		warn "Galaxy install failed on attempt ${attempt}. Trying git fallback."

		if ansible-galaxy collection install \
			-r "${REPO_ROOT}/requirements/requirements.git.yml" \
			-p "${collections_base_dir}" \
			--force-with-deps; then
			return 0
		fi

		if ((attempt >= max_attempts)); then
			warn "Unable to install required Ansible collections."
			return 1
		fi

		sleep_time=$((60 + RANDOM % 61))
		warn "Retrying collection installation in ${sleep_time}s."
		sleep "${sleep_time}"
		((attempt++))
	done
}

install_action_tools() {
	ensure_command actionlint
}

install_ansible_tools() {
	ensure_command ansible-playbook
	ensure_command ansible-galaxy
	ensure_required_ansible_collections
}

install_python_tools() {
	ensure_command shfmt
	ensure_command ruff
}

install_shellcheck_tools() {
	ensure_command shellcheck
}

install_requested_group() {
	local group="$1"

	case "${group}" in
	all)
		install_action_tools
		install_ansible_tools
		install_python_tools
		install_shellcheck_tools
		;;
	action)
		install_action_tools
		;;
	ansible)
		install_ansible_tools
		;;
	python)
		install_python_tools
		;;
	shellcheck)
		install_shellcheck_tools
		;;
	*)
		warn "Usage: $0 [all|action|ansible|python|shellcheck]..."
		return 2
		;;
	esac
}

main() {
	local groups=("$@")
	local group

	if [[ "${#groups[@]}" -eq 0 ]]; then
		groups=(all)
	fi

	for group in "${groups[@]}"; do
		install_requested_group "${group}"
	done
}

main "$@"
