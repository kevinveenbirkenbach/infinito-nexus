#!/usr/bin/env bash
set -euo pipefail
. /etc/os-release
echo ">>> Installing docker client on ID=${ID} ID_LIKE=${ID_LIKE:-}"

# shellcheck disable=SC2031
if [[ "${ID}" == "arch" || "${ID_LIKE:-}" =~ arch ]]; then
  pacman -Syu --noconfirm --needed docker
  pacman -Scc --noconfirm || true

elif [[ "${ID}" == "debian" || "${ID}" == "ubuntu" || "${ID_LIKE:-}" =~ debian ]]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    lsb-release
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/${ID}/gpg" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y --no-install-recommends docker-ce-cli
  rm -rf /var/lib/apt/lists/*

elif [[ "${ID}" == "fedora" ]]; then
  (dnf -y install docker-cli) || (dnf -y install moby-engine)
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
