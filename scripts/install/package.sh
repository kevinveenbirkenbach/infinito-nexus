#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f /etc/os-release ]]; then
	echo "[ERROR] /etc/os-release not found; unsupported system." >&2
	exit 1
fi

# shellcheck disable=SC1091
. /etc/os-release

run_privileged() {
	if [[ "${EUID}" -eq 0 ]]; then
		"$@"
	elif command -v sudo >/dev/null 2>&1; then
		sudo "$@"
	else
		"$@"
	fi
}

case "${ID:-}" in
	arch | manjaro)
		run_privileged pacman -Syu --noconfirm --needed make git curl bash sudo
		;;
	debian | ubuntu)
		run_privileged apt-get update
		run_privileged apt-get install -y --no-install-recommends make git curl bash sudo
		run_privileged rm -rf /var/lib/apt/lists/*
		;;
	fedora)
		run_privileged dnf -y install make git curl bash sudo
		run_privileged dnf -y clean all || true
		;;
	centos | rhel)
		if command -v dnf >/dev/null 2>&1; then
			run_privileged dnf -y install make git curl bash sudo
			run_privileged dnf -y clean all || true
		else
			run_privileged yum -y install make git curl bash sudo
		fi
		;;
	*)
		echo "[ERROR] Unsupported distro: ${ID:-unknown}" >&2
		exit 1
		;;
esac
