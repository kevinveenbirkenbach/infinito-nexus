ARG FEDIWALL_IMAGE
ARG FEDIWALL_VERSION
FROM ${FEDIWALL_IMAGE}:${FEDIWALL_VERSION}

ARG FEDIWALL_DIST_DIR_REL

# Static Fediwall release artefact (extracted from the upstream tarball)
COPY ./${FEDIWALL_DIST_DIR_REL}/ /usr/share/nginx/html/
