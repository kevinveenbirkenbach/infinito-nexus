# syntax=docker/dockerfile:1

# Hadolint: enforce explicit tag via separate repo + tag args
ARG INFINITO_IMAGE_REPO
ARG INFINITO_IMAGE_TAG

FROM ${INFINITO_IMAGE_REPO}:${INFINITO_IMAGE_TAG} AS full
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
