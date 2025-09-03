# Multi-stage build for castling.club

# Allow a dynamic base image version in both stages
ARG CHESS_VERSION

# -------- Stage 1: build --------
FROM node:${CHESS_VERSION} AS build

# Build-time inputs
ARG CHESS_REPO_URL
ARG CHESS_REPO_REF

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates openssl dumb-init python3 build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --depth 1 --branch "${CHESS_REPO_REF}" "${CHESS_REPO_URL}" ./

# Prepare Yarn 4 as root (safe during build stage)
RUN corepack enable && corepack prepare yarn@4.9.1 --activate && yarn -v
RUN yarn install --immutable --inline-builds
RUN yarn build

# -------- Stage 2: runtime --------
FROM node:${CHESS_VERSION}

# Runtime inputs (formerly Jinja variables)
ARG CHESS_ENTRYPOINT_REL
ARG CHESS_ENTRYPOINT_INT
ARG CHESS_APP_DATA_DIR
ARG CONTAINER_PORT

WORKDIR /app

# Minimal runtime deps + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash openssl dumb-init postgresql-client ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# Copy built app
COPY --from=build /src /app

# Install entrypoint
COPY ${CHESS_ENTRYPOINT_REL} ${CHESS_ENTRYPOINT_INT}
RUN chmod +x ${CHESS_ENTRYPOINT_INT}

# Fix: enable Corepack/Yarn as root so shims land in /usr/local/bin
RUN corepack enable && corepack prepare yarn@4.9.1 --activate && yarn -v

# Create writable dirs and set ownership
RUN mkdir -p ${CHESS_APP_DATA_DIR} /app/.yarn/cache /home/node \
 && chown -R node:node /app /home/node

# Use project-local Yarn cache
ENV YARN_ENABLE_GLOBAL_CACHE=false \
    YARN_CACHE_FOLDER=/app/.yarn/cache \
    HOME=/home/node

# Drop privileges
USER node

# Expose the runtime port (build-time constant)
EXPOSE ${CONTAINER_PORT}

ENTRYPOINT ["dumb-init", "--"]
# Use a shell so the value can be expanded reliably
ENV CHESS_ENTRYPOINT_INT=${CHESS_ENTRYPOINT_INT}
CMD ["sh","-lc","exec \"$CHESS_ENTRYPOINT_INT\""]
