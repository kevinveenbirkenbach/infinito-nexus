#!/usr/bin/env bash
# shellcheck shell=bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
ACTIONLINT_VERSION="${ACTIONLINT_VERSION:-latest}"
ACTIONLINT_INSTALL_DIR="${ACTIONLINT_INSTALL_DIR:-/usr/local/bin}"

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

detect_python_bin() {
	local python_bin="${PYTHON:-python3}"

	if command -v "${python_bin}" >/dev/null 2>&1; then
		printf '%s\n' "${python_bin}"
		return 0
	fi

	if command -v python3 >/dev/null 2>&1; then
		printf 'python3\n'
		return 0
	fi

	if command -v python >/dev/null 2>&1; then
		printf 'python\n'
		return 0
	fi

	warn "Need python, python3, curl, or wget."
	return 1
}

download_file() {
	local url="$1"
	local output="$2"
	local python_bin

	if command -v curl >/dev/null 2>&1; then
		curl -fsSL "${url}" -o "${output}"
		return 0
	fi

	if command -v wget >/dev/null 2>&1; then
		wget -qO "${output}" "${url}"
		return 0
	fi

	python_bin="$(detect_python_bin)" || {
		warn "Need curl, wget, or python to download ${url}."
		return 1
	}

	"${python_bin}" - "${url}" "${output}" <<'PY'
import pathlib
import sys
from urllib.request import urlopen

url, output = sys.argv[1], sys.argv[2]
with urlopen(url) as response:
    pathlib.Path(output).write_bytes(response.read())
PY
}

resolve_latest_actionlint_version() {
	local latest_url="https://github.com/rhysd/actionlint/releases/latest"
	local final_url=""
	local python_bin

	if command -v curl >/dev/null 2>&1; then
		final_url="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "${latest_url}")"
	elif command -v wget >/dev/null 2>&1; then
		final_url="$(
			wget -q --server-response --max-redirect=0 -O /dev/null "${latest_url}" 2>&1 |
				sed -n 's/^[[:space:]]*Location: //p' |
				tr -d '\r' |
				tail -n1
		)"
	else
		python_bin="$(detect_python_bin)" || return 1
		final_url="$(
			"${python_bin}" - "${latest_url}" <<'PY'
import sys
from urllib.request import urlopen

with urlopen(sys.argv[1]) as response:
    print(response.geturl())
PY
		)"
	fi

	final_url="${final_url%/}"
	if [[ -z "${final_url}" ]]; then
		warn "Failed to resolve latest actionlint release URL."
		return 1
	fi

	if [[ "${final_url}" == "${latest_url}" ]]; then
		warn "Latest actionlint release URL did not resolve to a versioned tag."
		return 1
	fi

	local latest_tag="${final_url##*/}"
	latest_tag="${latest_tag#v}"

	if [[ -z "${latest_tag}" || "${latest_tag}" == "${final_url}" || "${latest_tag}" == "latest" ]]; then
		warn "Failed to determine latest actionlint version from ${final_url}."
		return 1
	fi

	printf '%s\n' "${latest_tag}"
}

resolve_actionlint_version() {
	local requested="${ACTIONLINT_VERSION#v}"

	if [[ "${requested}" != "latest" ]]; then
		printf '%s\n' "${requested}"
		return 0
	fi

	resolve_latest_actionlint_version
}

detect_actionlint_os() {
	case "$(uname -s)" in
	Linux)
		printf 'linux\n'
		;;
	Darwin)
		printf 'darwin\n'
		;;
	FreeBSD)
		printf 'freebsd\n'
		;;
	*)
		warn "Unsupported OS for actionlint prebuilt binary: $(uname -s)"
		return 1
		;;
	esac
}

detect_actionlint_arch() {
	case "$(uname -m)" in
	x86_64 | amd64)
		printf 'amd64\n'
		;;
	i386 | i486 | i586 | i686)
		printf '386\n'
		;;
	aarch64 | arm64)
		printf 'arm64\n'
		;;
	armv6l | armv7l)
		printf 'armv6\n'
		;;
	*)
		warn "Unsupported architecture for actionlint prebuilt binary: $(uname -m)"
		return 1
		;;
	esac
}

ensure_dir_on_path() {
	local dir="$1"

	case ":${PATH}:" in
	*:"${dir}":*) ;;
	*)
		export PATH="${dir}:${PATH}"
		;;
	esac
}

install_with_optional_sudo() {
	if "$@"; then
		return 0
	fi

	run_privileged "$@"
}

install_actionlint_binary() {
	local version
	local os
	local arch
	local archive_name
	local url
	local tmpdir
	local archive_path

	version="$(resolve_actionlint_version)" || return 1
	os="$(detect_actionlint_os)" || return 1
	arch="$(detect_actionlint_arch)" || return 1
	archive_name="actionlint_${version}_${os}_${arch}.tar.gz"
	url="https://github.com/rhysd/actionlint/releases/download/v${version}/${archive_name}"
	tmpdir="$(mktemp -d)"
	archive_path="${tmpdir}/${archive_name}"

	if [[ "${ACTIONLINT_VERSION#v}" == "latest" ]]; then
		log "Installing latest actionlint (resolved to v${version}) from GitHub releases"
	else
		log "Installing actionlint v${version} from GitHub releases"
	fi

	if ! download_file "${url}" "${archive_path}"; then
		warn "Failed to download ${url}"
		rm -rf "${tmpdir}"
		return 1
	fi

	if ! tar -xzf "${archive_path}" -C "${tmpdir}"; then
		warn "Failed to extract ${archive_name}"
		rm -rf "${tmpdir}"
		return 1
	fi

	if [[ ! -f "${tmpdir}/actionlint" ]]; then
		warn "Archive ${archive_name} did not contain an actionlint binary."
		rm -rf "${tmpdir}"
		return 1
	fi

	if ! install_with_optional_sudo install -d "${ACTIONLINT_INSTALL_DIR}"; then
		warn "Failed to create ${ACTIONLINT_INSTALL_DIR}"
		rm -rf "${tmpdir}"
		return 1
	fi

	if ! install_with_optional_sudo install -m 0755 "${tmpdir}/actionlint" "${ACTIONLINT_INSTALL_DIR}/actionlint"; then
		warn "Failed to install actionlint into ${ACTIONLINT_INSTALL_DIR}"
		rm -rf "${tmpdir}"
		return 1
	fi

	rm -rf "${tmpdir}"
}

ensure_actionlint() {
	if command -v actionlint >/dev/null 2>&1; then
		return 0
	fi

	log "Missing command 'actionlint'. Installing official prebuilt binary."
	install_actionlint_binary || {
		warn "Installation failed for 'actionlint'."
		return 1
	}

	ensure_dir_on_path "${ACTIONLINT_INSTALL_DIR}"
	hash -r

	command -v actionlint >/dev/null 2>&1 || {
		warn "Command 'actionlint' is still unavailable after installation."
		return 1
	}
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
	ensure_actionlint
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
