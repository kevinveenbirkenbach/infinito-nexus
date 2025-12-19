# syntax=docker/dockerfile:1

# Hadolint: enforce explicit tag via separate repo + tag args
ARG INFINITO_IMAGE_REPO
ARG INFINITO_IMAGE_TAG

FROM ${INFINITO_IMAGE_REPO}:${INFINITO_IMAGE_TAG} AS full
SHELL ["/bin/bash", "-lc"]

RUN cat /etc/os-release || true

# ------------------------------------------------------------
# Install Docker CLI (client only) - distro aware
# ------------------------------------------------------------
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
    apt-get install -y --no-install-recommends ca-certificates curl gnupg lsb-release; \
    install -m 0755 -d /etc/apt/keyrings; \
    curl -fsSL https://download.docker.com/linux/${ID}/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg; \
    chmod a+r /etc/apt/keyrings/docker.gpg; \
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} \
      $(. /etc/os-release && echo ${VERSION_CODENAME}) stable" \
      > /etc/apt/sources.list.d/docker.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends docker-ce-cli; \
    rm -rf /var/lib/apt/lists/*; \
  \
  elif [[ "${ID}" == "fedora" || "${ID_LIKE:-}" =~ fedora ]]; then \
    # Fedora: docker client via docker-cli or moby-engine
    dnf -y install ca-certificates curl; \
    (dnf -y install docker-cli) || (dnf -y install moby-engine); \
    dnf -y clean all; \
    rm -rf /var/cache/dnf; \
  \
  elif [[ "${ID}" == "centos" || "${ID}" == "rhel" || "${ID_LIKE:-}" =~ (rhel|centos|fedora) ]]; then \
    # CentOS/RHEL-like
    if command -v dnf >/dev/null 2>&1; then PM=dnf; else PM=yum; fi; \
    ${PM} -y install ca-certificates curl; \
    ${PM} -y install yum-utils || true; \
    ${PM} -y install dnf-plugins-core || true; \
    ( ${PM} config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo ) || true; \
    ( ${PM} -y install docker-ce-cli ) || ( ${PM} -y install docker ); \
    ${PM} -y clean all || true; \
    rm -rf /var/cache/${PM} || true; \
  \
  else \
    echo "[ERROR] Unsupported distro for docker client install: ID=${ID} ID_LIKE=${ID_LIKE:-}" >&2; \
    exit 1; \
  fi; \
  \
  echo ">>> docker version (client):"; \
  docker version || true

# ------------------------------------------------------------
# Infinito.Nexus source in
# ------------------------------------------------------------
COPY . /opt/src/infinito

# ------------------------------------------------------------
# Install infinito via pkgmgr (shallow)
# ------------------------------------------------------------
RUN set -euo pipefail; \
  pkgmgr install infinito --clone-mode shallow

# ------------------------------------------------------------
# Override with local source
# ------------------------------------------------------------
RUN set -euo pipefail; \
  INFINITO_PATH="$(pkgmgr path infinito)"; \
  : "${INFINITO_PATH:?}"; \
  test "${INFINITO_PATH}" != "/"; \
  rm -rf -- "${INFINITO_PATH:?}/"*; \
  rsync -a --delete --exclude='.git' /opt/src/infinito/ "${INFINITO_PATH:?}/"; \
  make -C "${INFINITO_PATH:?}" install

ENV PATH="/opt/venvs/infinito/bin:${PATH}"

ENTRYPOINT ["/opt/src/infinito/scripts/docker/entry.sh"]
CMD ["infinito", "--help"]
