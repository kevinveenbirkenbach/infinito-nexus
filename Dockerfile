# syntax=docker/dockerfile:1

ARG INFINITO_DISTRO
ARG INFINITO_IMAGE_BASE

FROM ${INFINITO_IMAGE_BASE} AS full
SHELL ["/bin/bash", "-lc"]

RUN cat /etc/os-release || true

# ------------------------------------------------------------
# Infinito.Nexus source in
# ------------------------------------------------------------
COPY . /opt/src/infinito

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
  rsync -a --delete --exclude='.git' /opt/src/infinito/ "${INFINITO_PATH}/"; \
  cd "${INFINITO_PATH}/"; \
  make install;

ENV PATH="/opt/venvs/infinito/bin:${PATH}"

ENTRYPOINT ["/opt/src/infinito/scripts/docker/entry.sh"]
CMD ["infinito", "--help"]
