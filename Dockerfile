# syntax=docker/dockerfile:1

# Hadolint: enforce explicit tag via separate repo + tag args
ARG INFINITO_IMAGE_REPO
ARG INFINITO_IMAGE_TAG

FROM ${INFINITO_IMAGE_REPO}:${INFINITO_IMAGE_TAG} AS full
SHELL ["/bin/bash", "-lc"]

RUN cat /etc/os-release || true

# ------------------------------------------------------------
# Controller essentials:
# - docker CLI: controls host Docker via /var/run/docker.sock
# - ssh-keygen: generate ephemeral SSH key for deploy tests
# ------------------------------------------------------------
RUN set -euo pipefail; \
  if command -v pacman >/dev/null 2>&1; then \
    pacman -Syu --noconfirm --needed docker openssh; \
    pacman -Scc --noconfirm || true; \
  elif command -v apt-get >/dev/null 2>&1; then \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends docker.io openssh-client; \
    rm -rf /var/lib/apt/lists/*; \
  elif command -v dnf >/dev/null 2>&1; then \
    dnf -y install docker openssh-clients; \
    dnf clean all; \
  elif command -v yum >/dev/null 2>&1; then \
    yum -y install docker openssh-clients; \
    yum clean all; \
  elif command -v apk >/dev/null 2>&1; then \
    apk add --no-cache docker-cli openssh-client; \
  else \
    echo "[ERROR] No supported package manager found to install controller tools." >&2; \
    exit 1; \
  fi

# ------------------------------------------------------------
# Infinito.Nexus source in
# ------------------------------------------------------------
COPY . /opt/src/infinito

# ------------------------------------------------------------
# Install infinito via pkgmgr (shallow) - CI-safe
# ------------------------------------------------------------
RUN set -euo pipefail; \
  pkgmgr install infinito --clone-mode shallow --no-verification

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
