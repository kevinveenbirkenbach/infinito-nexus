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
# Infinito.Nexus source in
# ------------------------------------------------------------
COPY . ${INFINITO_SRC_DIR}

# ------------------------------------------------------------
# Install Docker CLI (client only) - distro aware
# ------------------------------------------------------------
# hadolint ignore=DL3008,DL3041
RUN /bin/bash ${INFINITO_SRC_DIR}/roles/sys-svc-docker/files/install-cli.sh

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
