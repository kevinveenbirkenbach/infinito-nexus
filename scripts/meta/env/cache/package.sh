#!/usr/bin/env bash
# shellcheck shell=bash
# Package-cache env defaults. See docs/contributing/environment/cache.md.

set -euo pipefail

: "${INFINITO_PACKAGE_CACHE_HOST_PATH:=/var/cache/infinito/core/cache/package/data}"
export INFINITO_PACKAGE_CACHE_HOST_PATH

# JVM heap: half free RAM, capped at 2g, floor 1g (Nexus 3 OSS minimum).
if [[ -z "${INFINITO_PACKAGE_CACHE_HEAP:-}" ]]; then
	_pc_avail_ram_mb="$(awk '/^MemAvailable:/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)"
	if [[ "${_pc_avail_ram_mb}" -le 0 ]]; then
		_pc_heap_gb=1
	else
		_pc_heap_gb=$((_pc_avail_ram_mb / 2048))
		if [[ "${_pc_heap_gb}" -lt 1 ]]; then _pc_heap_gb=1; fi
		if [[ "${_pc_heap_gb}" -gt 2 ]]; then _pc_heap_gb=2; fi
	fi
	INFINITO_PACKAGE_CACHE_HEAP="${_pc_heap_gb}g"
	unset _pc_avail_ram_mb _pc_heap_gb
fi
export INFINITO_PACKAGE_CACHE_HEAP

if [[ -z "${INFINITO_PACKAGE_CACHE_DIRECT_MEM:-}" ]]; then
	INFINITO_PACKAGE_CACHE_DIRECT_MEM="${INFINITO_PACKAGE_CACHE_HEAP}"
fi
export INFINITO_PACKAGE_CACHE_DIRECT_MEM

# Blobstore quota: half free disk at cache path, floor 2g.
if [[ -z "${INFINITO_PACKAGE_CACHE_BLOBSTORE_MAX:-}" ]]; then
	_pc_path="${INFINITO_PACKAGE_CACHE_HOST_PATH}"
	while [[ ! -d "${_pc_path}" && "${_pc_path}" != "/" && "${_pc_path}" != "." ]]; do
		_pc_path="$(dirname "${_pc_path}")"
	done
	_pc_avail_gb="$(df --output=avail -B1G "${_pc_path}" 2>/dev/null | awk 'NR==2 {print $1+0}')"
	if [[ -z "${_pc_avail_gb}" || "${_pc_avail_gb}" -le 0 ]]; then _pc_avail_gb=4; fi
	_pc_half_gb=$((_pc_avail_gb / 2))
	if [[ "${_pc_half_gb}" -lt 2 ]]; then _pc_half_gb=2; fi
	INFINITO_PACKAGE_CACHE_BLOBSTORE_MAX="${_pc_half_gb}g"
	unset _pc_path _pc_avail_gb _pc_half_gb
fi
export INFINITO_PACKAGE_CACHE_BLOBSTORE_MAX

# Use `hostname` command, not $HOSTNAME var, so subshells see the same value.
if [[ -z "${INFINITO_PACKAGE_CACHE_ADMIN_PASSWORD:-}" ]]; then
	_pc_host="$(hostname 2>/dev/null || echo local)"
	_pc_seed="${INFINITO_PACKAGE_CACHE_HOST_PATH}:${_pc_host}"
	INFINITO_PACKAGE_CACHE_ADMIN_PASSWORD="$(printf '%s' "${_pc_seed}" | sha256sum | awk '{print substr($1,1,32)}')"
	unset _pc_seed _pc_host
fi
export INFINITO_PACKAGE_CACHE_ADMIN_PASSWORD

: "${INFINITO_PACKAGE_CACHE_PORT:=8081}"
export INFINITO_PACKAGE_CACHE_PORT

: "${INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR:=/var/cache/infinito/core/cache/package/frontend/ca}"
: "${INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR:=/var/cache/infinito/core/cache/package/frontend/certs}"
export INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR
export INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR

: "${INFINITO_PACKAGE_CACHE_FRONTEND_IP:=172.30.0.4}"
export INFINITO_PACKAGE_CACHE_FRONTEND_IP

# Cache freshness in minutes; 129600 = 90 days.
: "${INFINITO_PACKAGE_CACHE_MAX_AGE_MIN:=129600}"
export INFINITO_PACKAGE_CACHE_MAX_AGE_MIN
