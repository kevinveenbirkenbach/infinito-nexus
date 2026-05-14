#!/usr/bin/env bash
# Source-able helper for local deploy/update scripts:
#
#   deploy_with_cache_retry <label> -- <cmd> [args...]
#
# Runs the wrapped command and watches its combined stdout+stderr for the
# stale-apt signature
#
#   "Release file ... is expired"  /  "Valid-Until ... expired"
#
# which surfaces when the registry-cache or package-cache (Nexus / nginx
# frontend) serves apt repository metadata whose `Valid-Until` window has
# elapsed — usually because the cache has not refreshed since the last
# `apt-get update` ran upstream, or the host clock has drifted past the
# Release file's validity. The result is a Docker-build failure like
#
#   E: Release file for http://deb.debian.org/debian/dists/bookworm-updates/InRelease
#      is expired (invalid since 5h 30min 54s).
#
# On match, the helper wipes BOTH cache stacks via `make cache-clean`
# (registry-cache + package-cache via scripts/system/cache/clean.sh),
# prunes the local Docker builder cache + unused images, and re-runs the
# wrapped command exactly once. Stale-cache detection is the ONLY retry
# trigger; any other failure bubbles straight up so the deploy/update
# script's existing error handling is preserved.
#
# The wrapped command MUST be idempotent enough to tolerate a single
# re-execution. Both `python -m cli.administration.deploy.development
# deploy` and the pre-cleanup steps in our deploy scripts satisfy that.

# shellcheck shell=bash

_cache_retry_stale_pattern='Release file .*is expired|Valid-Until.*expired'

cache_retry_wipe_all() {
	local repo_root="${1:-${PWD}}"
	echo "[cache-retry] make cache-clean (registry-cache + package-cache)..."
	(cd "${repo_root}" && make cache-clean) || true
	echo "[cache-retry] docker builder prune -af (drop cached build layers)..."
	docker builder prune -af >/dev/null 2>&1 || true
	echo "[cache-retry] docker image prune -af (drop unused base images)..."
	docker image prune -af >/dev/null 2>&1 || true
}

# Run `"$@" 2>&1 | tee <log>` defensively: the caller's `set -e` plus the
# global `set -o pipefail` would otherwise kill the script the moment the
# wrapped command exits non-zero — *before* the helper can decide whether
# the failure matches the stale-cache signature. Toggle `set +e` only
# around the pipeline and restore the caller's original errexit state so
# the helper never silently changes it.
#
# Sets globals: __cache_retry_rc (wrapped command's true exit code).
_cache_retry_run_capture() {
	local log="$1"
	shift
	__cache_retry_rc=0
	local _prev_e=0
	[[ $- == *e* ]] && _prev_e=1
	set +e
	"$@" 2>&1 | tee "${log}"
	__cache_retry_rc=${PIPESTATUS[0]}
	[[ "${_prev_e}" -eq 1 ]] && set -e
	return 0
}

# Usage: deploy_with_cache_retry "<label>" -- "$@"
deploy_with_cache_retry() {
	local label="${1:-deploy}"
	shift
	if [[ "${1:-}" == "--" ]]; then shift; fi

	local repo_root="${REPO_ROOT:-${PWD}}"
	local log
	log="$(mktemp -t "deploy-${label//[^A-Za-z0-9._-]/-}.XXXXXX.log")"

	_cache_retry_run_capture "${log}" "$@"
	local rc=${__cache_retry_rc}

	if [[ "${rc}" -eq 0 ]]; then
		rm -f "${log}"
		return 0
	fi

	if ! grep -qE "${_cache_retry_stale_pattern}" "${log}" 2>/dev/null; then
		# Non-stale-cache failure: bubble up as-is.
		rm -f "${log}"
		return "${rc}"
	fi

	echo
	echo "[cache-retry] Stale apt Release file detected in '${label}' output."
	echo "[cache-retry] Wiping registry+package cache, Docker builder cache, unused images,"
	echo "[cache-retry] then re-running the command exactly once."
	cache_retry_wipe_all "${repo_root}"

	echo
	echo "[cache-retry] Re-running: ${label}"
	: >"${log}"
	_cache_retry_run_capture "${log}" "$@"
	rc=${__cache_retry_rc}

	rm -f "${log}"
	return "${rc}"
}
