# syntax=docker/dockerfile:1

ARG PKGMGR_IMAGE_REPO=ghcr.io/kevinveenbirkenbach/pkgmgr-arch
ARG PKGMGR_IMAGE_TAG=stable

FROM ${PKGMGR_IMAGE_REPO}:${PKGMGR_IMAGE_TAG} AS full

# Hadolint DL4006: ensure pipefail is set for RUN instructions that use pipes
SHELL ["/bin/bash", "-o", "pipefail", "-lc"]

# Forwardable build-time Nix settings (e.g., GitHub access tokens to avoid rate limits)
ARG NIX_CONFIG

ENV INFINITO_SRC_DIR="/opt/src/infinito"
ENV PYTHON="/opt/venvs/infinito/bin/python"
ENV PIP="/opt/venvs/infinito/bin/python -m pip"
ENV PATH="/opt/venvs/infinito/bin:${PATH}"

RUN cat /etc/os-release || true

# ------------------------------------------------------------
# Install Docker CLI (client only) - distro aware
# ------------------------------------------------------------
# hadolint ignore=DL3008,DL3041
RUN set -euo pipefail; \
  . /etc/os-release; \
  echo ">>> Installing docker client on ID=${ID} ID_LIKE=${ID_LIKE:-}"; \
  \
  if [[ "${ID}" == "arch" || "${ID_LIKE:-}" =~ arch ]]; then \
    # Arch: docker CLI already pulls required deps in non-virgin images
    pacman -Syu --noconfirm --needed docker; \
    pacman -Scc --noconfirm || true; \
  \
  elif [[ "${ID}" == "debian" || "${ID}" == "ubuntu" || "${ID_LIKE:-}" =~ debian ]]; then \
    # Debian/Ubuntu: use Docker official repo for docker-ce-cli
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      curl \
      gnupg \
      lsb-release; \
    install -m 0755 -d /etc/apt/keyrings; \
    curl -fsSL "https://download.docker.com/linux/${ID}/gpg" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg; \
    chmod a+r /etc/apt/keyrings/docker.gpg; \
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} \
      $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" \
      > /etc/apt/sources.list.d/docker.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends docker-ce-cli; \
    rm -rf /var/lib/apt/lists/*; \
  \
  elif [[ "${ID}" == "fedora" ]]; then \
    # Fedora: docker client via docker-cli or moby-engine
    (dnf -y install docker-cli) || (dnf -y install moby-engine); \
    dnf -y clean all; \
    rm -rf /var/cache/dnf; \
  \
  elif [[ "${ID}" == "centos" || "${ID}" == "rhel" || "${ID_LIKE:-}" =~ (rhel|centos) ]]; then \
    # CentOS/RHEL-like
    if command -v dnf >/dev/null 2>&1; then PM=dnf; else PM=yum; fi; \
    ${PM} -y install yum-utils || true; \
    ${PM} -y install dnf-plugins-core || true; \
    ( ${PM} config-manager --add-repo "https://download.docker.com/linux/centos/docker-ce.repo" ) || true; \
    ( ${PM} -y install docker-ce-cli ) || ( ${PM} -y install docker ); \
    ${PM} -y clean all || true; \
    rm -rf "/var/cache/${PM}" || true; \
  \
  else \
    echo "[ERROR] Unsupported distro for docker client install: ID=${ID} ID_LIKE=${ID_LIKE:-}" >&2; \
    exit 1; \
  fi

# ------------------------------------------------------------
# Infinito.Nexus source in
# ------------------------------------------------------------
COPY . ${INFINITO_SRC_DIR}

# ------------------------------------------------------------
# Install infinito via pkgmgr (shallow)
# ------------------------------------------------------------
RUN set -euo pipefail; \
  export NIX_CONFIG="${NIX_CONFIG:-}"; \
  echo "[docker-infinito] Install Infinito.Nexus via pkgmgr"; \
  pkgmgr install infinito --clone-mode shallow; \
  echo "[docker-infinito] Installed Infinito.Nexus Version:"; \
  pkgmgr version infinito

# ------------------------------------------------------------
# Override with local source
# ------------------------------------------------------------
RUN set -euo pipefail; \
  export NIX_CONFIG="${NIX_CONFIG:-}"; \
  INSTALL_LOCAL_BUILD=1 /opt/src/infinito/scripts/docker/entry.sh true

# Set workdir to / to avoid ambiguous commands
WORKDIR /

ENTRYPOINT ["/opt/src/infinito/scripts/docker/entry.sh"]
CMD ["infinito", "--help"]
