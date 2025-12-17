# syntax=docker/dockerfile:1

ARG PKGMGR_DISTRO=arch

ARG PKGMGR_IMAGE_OWNER=kevinveenbirkenbach
ARG PKGMGR_IMAGE_TAG=stable
ARG PKGMGR_IMAGE="ghcr.io/${PKGMGR_IMAGE_OWNER}/pkgmgr-${PKGMGR_DISTRO}:${PKGMGR_IMAGE_TAG}"

FROM ${PKGMGR_IMAGE} AS infinito
SHELL ["/bin/bash", "-lc"]

RUN cat /etc/os-release || true

# ------------------------------------------------------------
# Infinito.Nexus source in
# ------------------------------------------------------------
COPY . /opt/infinito-src

# ------------------------------------------------------------
# Install infinito via pkgmgr (shallow)
# ------------------------------------------------------------
RUN set -euo pipefail; \
  pkgmgr install infinito --clone-mode shallow;

# ------------------------------------------------------------
# Override with local source
# ------------------------------------------------------------
RUN set -euo pipefail; \
  INFINITO_PATH="$(pkgmgr path infinito)"; \
  rm -rf "${INFINITO_PATH}/"*; \
  rsync -a --delete --exclude='.git' /opt/infinito-src/ "${INFINITO_PATH}/"; \
  ln -sf "${INFINITO_PATH}/main.py" /usr/local/bin/infinito; \
  chmod +x /usr/local/bin/infinito; \
  cd "${INFINITO_PATH}/"; \
  make install;

# ------------------------------------------------------------
# Verify Installation
# ------------------------------------------------------------
RUN infinito --help

CMD ["bash", "-lc", "infinito --help && exec tail -f /dev/null"]
