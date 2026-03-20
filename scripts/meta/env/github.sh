#!/usr/bin/env bash
# shellcheck shell=bash
#
# Resolve GitHub/Act specific overrides.

set -euo pipefail

if [[ "${INFINITO_ENV_GITHUB_LOADED:-}" == "1" ]]; then
	return 0
fi
export INFINITO_ENV_GITHUB_LOADED="1"

: "${RUNNING_ON_GITHUB:=false}"

if [[ "${RUNNING_ON_GITHUB}" == "true" ]]; then
	: "${INFINITO_PULL_POLICY:=always}"
	: "${INFINITO_IMAGE_TAG:=latest}"

	_owner="${GITHUB_REPOSITORY_OWNER:-${OWNER:-}}"
	_owner="${_owner,,}"
	: "${INFINITO_IMAGE:=ghcr.io/${_owner}/infinito-${INFINITO_DISTRO}:${INFINITO_IMAGE_TAG}}"

	: "${INFINITO_NO_BUILD:=1}"
	: "${INFINITO_DOCKER_VOLUME:=/mnt/docker}"
	: "${INFINITO_DOCKER_MOUNT:=/var/lib/docker}"
	: "${INFINITO_COMPILE:=0}"

	export INFINITO_PULL_POLICY INFINITO_IMAGE_TAG INFINITO_IMAGE INFINITO_NO_BUILD
	export INFINITO_DOCKER_VOLUME INFINITO_DOCKER_MOUNT
	export INFINITO_COMPILE
else
	: "${INFINITO_COMPILE:=1}"
	export INFINITO_COMPILE
fi

if [[ -n "${NIX_CONFIG:-}" ]]; then
	export NIX_CONFIG
fi
