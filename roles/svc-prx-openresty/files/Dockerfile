ARG OPENRESTY_IMAGE=openresty/openresty
ARG OPENRESTY_VERSION=alpine
FROM ${OPENRESTY_IMAGE}:${OPENRESTY_VERSION}

# Build-time flag — set to "true" only when prometheus is active in the deployment.
# Gating the download here avoids adding lua-resty-prometheus to images that do
# not use it, and lets the mirror system substitute the URLs via build args.
# Accepts: true, True, TRUE, 1, yes (case-insensitive via shell case).
ARG PROMETHEUS_ENABLED=false
ARG LUA_PROMETHEUS_URL_MAIN=https://raw.githubusercontent.com/knyar/nginx-lua-prometheus/master/prometheus.lua
ARG LUA_PROMETHEUS_URL_COUNTER=https://raw.githubusercontent.com/knyar/nginx-lua-prometheus/master/prometheus_resty_counter.lua
ARG LUA_PROMETHEUS_URL_KEYS=https://raw.githubusercontent.com/knyar/nginx-lua-prometheus/master/prometheus_keys.lua

RUN case "${PROMETHEUS_ENABLED}" in \
      true|True|TRUE|1|yes) \
        apk add --no-cache wget \
        && mkdir -p /usr/local/openresty/lualib/resty \
        && wget -q -O /usr/local/openresty/lualib/resty/prometheus.lua "$LUA_PROMETHEUS_URL_MAIN" \
        && wget -q -O /usr/local/openresty/lualib/prometheus_resty_counter.lua "$LUA_PROMETHEUS_URL_COUNTER" \
        && wget -q -O /usr/local/openresty/lualib/prometheus_keys.lua "$LUA_PROMETHEUS_URL_KEYS" \
        ;; \
    esac
