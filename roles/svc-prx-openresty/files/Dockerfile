ARG OPENRESTY_IMAGE
ARG OPENRESTY_VERSION
FROM ${OPENRESTY_IMAGE}:${OPENRESTY_VERSION}

# Build-time flag — set to "true" only when prometheus is active in the deployment.
# Gating the download here avoids adding lua-resty-prometheus to images that do
# not use it, and lets the mirror system substitute the URLs via build args.
# Accepts: true, True, TRUE, 1, yes (case-insensitive via shell case).
# All values are passed via compose.yml.j2 build args; SPOT is config/main.yml.
ARG PROMETHEUS_ENABLED
ARG LUA_PROMETHEUS_URL_MAIN
ARG LUA_PROMETHEUS_URL_COUNTER
ARG LUA_PROMETHEUS_URL_KEYS

RUN case "${PROMETHEUS_ENABLED}" in \
      true|True|TRUE|1|yes) \
        apk add --no-cache wget \
        && mkdir -p /usr/local/openresty/lualib/resty \
        && wget -q -O /usr/local/openresty/lualib/resty/prometheus.lua "$LUA_PROMETHEUS_URL_MAIN" \
        && wget -q -O /usr/local/openresty/lualib/prometheus_resty_counter.lua "$LUA_PROMETHEUS_URL_COUNTER" \
        && wget -q -O /usr/local/openresty/lualib/prometheus_keys.lua "$LUA_PROMETHEUS_URL_KEYS" \
        ;; \
    esac
