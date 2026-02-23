#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
. /etc/os-release

echo ">>> Installing docker client on ID=${ID} ID_LIKE=${ID_LIKE:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_APT_SANITIZER="${SCRIPT_DIR}/apt_repo.sh"

sanitize_docker_apt_sources() {
  local distro_id="$1"
  local keep_canonical="${2:-1}"

  bash "${DOCKER_APT_SANITIZER}" sanitize-sources "${distro_id}" "${keep_canonical}" >/dev/null
}

ensure_docker_apt_key_and_sources() {
  local distro_id="$1"
  local keep_canonical="${2:-1}"

  bash "${DOCKER_APT_SANITIZER}" ensure-key-and-sanitize "${distro_id}" "${keep_canonical}" >/dev/null
}

# shellcheck disable=SC2031
if [[ "${ID}" == "arch" || "${ID_LIKE:-}" =~ arch ]]; then
  pacman -Syu --noconfirm --needed docker
  pacman -Scc --noconfirm || true

elif [[ "${ID}" == "debian" || "${ID}" == "ubuntu" || "${ID_LIKE:-}" =~ debian ]]; then
  export DEBIAN_FRONTEND=noninteractive
  sanitize_docker_apt_sources "${ID}" 0
  apt-get update
  apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    lsb-release
  ensure_docker_apt_key_and_sources "${ID}" 1

  # shellcheck disable=SC1091
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${ID} $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y --no-install-recommends docker-ce-cli
  rm -rf /var/lib/apt/lists/*

elif [[ "${ID}" == "fedora" ]]; then
  dnf -y install dnf-plugins-core
  dnf config-manager --add-repo "https://download.docker.com/linux/fedora/docker-ce.repo"
  dnf -y install --allowerasing docker-ce-cli docker-buildx-plugin docker-compose-plugin
  dnf -y clean all
  rm -rf /var/cache/dnf

elif [[ "${ID}" == "centos" || "${ID}" == "rhel" || "${ID_LIKE:-}" =~ (rhel|centos) ]]; then
  if command -v dnf >/dev/null 2>&1; then PM=dnf; else PM=yum; fi
  ${PM} -y install yum-utils || true
  ${PM} -y install dnf-plugins-core || true
  (${PM} config-manager --add-repo "https://download.docker.com/linux/centos/docker-ce.repo") || true
  (${PM} -y install docker-ce-cli) || (${PM} -y install docker) || true
  ${PM} -y clean all || true
  rm -rf "/var/cache/${PM}" || true

else
  echo "[ERROR] Unsupported distro for docker client install: ID=${ID} ID_LIKE=${ID_LIKE:-}" >&2
  exit 1
fi
