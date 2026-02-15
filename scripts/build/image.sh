#!/usr/bin/env bash
set -euo pipefail

: "${INFINITO_DISTRO:?Environment variable 'INFINITO_DISTRO' must be set (arch|debian|ubuntu|fedora|centos)}"

NO_CACHE=0
MISSING_ONLY=0

# New: build variant
VARIANT="full"         # full | slim

# Keep --target for advanced usage, but default is derived from VARIANT.
TARGET=""
IMAGE_TAG=""           # local image name or base tag (without registry)
PUSH=0                 # if 1 -> use buildx and push (requires docker buildx)
PUBLISH=0              # if 1 -> push with semantic tags (latest/version/stable + aliases)
REGISTRY=""            # e.g. ghcr.io
OWNER=""               # e.g. github org/user
REPO_PREFIX="infinito" # image base name (infinito)
VERSION=""             # X.Y.Z (required for --publish)
IS_STABLE="false"      # "true" -> publish stable tags
DEFAULT_DISTRO="debian"

# Base pkgmgr image selection
PKGMGR_IMAGE_OWNER="kevinveenbirkenbach"
PKGMGR_IMAGE_TAG="stable" # can be overridden by env or future flag
PKGMGR_IMAGE=""           # computed below (single build-arg for Dockerfile)

usage() {
	local default_tag="${REPO_PREFIX}-${INFINITO_DISTRO}"
	if [[ "${VARIANT}" == "slim" ]]; then
		default_tag="${default_tag}-slim"
	fi
	if [[ -n "${TARGET:-}" ]]; then
		default_tag="${default_tag}-${TARGET}"
	fi

	cat <<EOF
Usage: INFINITO_DISTRO=<distro> $0 [options]

Build options:
  --variant <full|slim> Build full or slim image (default: full)
  --missing             Build only if the image does not already exist (local build only)
  --no-cache            Build with --no-cache
  --target <name>       Override Dockerfile target (advanced). Default derived from --variant.
  --tag <image>         Override the output image tag (default: ${default_tag})

Publish options:
  --push                Push the built image (uses docker buildx build --push)
  --publish             Publish semantic tags (latest, <version>, optional stable) + default-distro aliases
  --registry <reg>      Registry (e.g. ghcr.io)
  --owner <owner>       Registry namespace (e.g. \${GITHUB_REPOSITORY_OWNER})
  --repo-prefix <name>  Image base name (default: infinito)
  --version <X.Y.Z>     Version for --publish
  --stable <true|false> Whether to publish :stable tags (default: false)

Notes:
- --publish implies --push and requires --registry, --owner, and --version.
- Local build (no --push) uses "docker build" and creates local images like "infinito-arch" / "infinito-arch-slim".
- If you set NIX_CONFIG in the environment (e.g. access-tokens), it will be forwarded into the build.
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	--variant)
		VARIANT="${2:-}"
		[[ "${VARIANT}" == "full" || "${VARIANT}" == "slim" ]] || {
			echo "ERROR: --variant must be 'full' or 'slim'" >&2
			exit 2
		}
		shift 2
		;;
	--no-cache)
		NO_CACHE=1
		shift
		;;
	--missing)
		MISSING_ONLY=1
		shift
		;;
	--target)
		TARGET="${2:-}"
		[[ -n "${TARGET}" ]] || { echo "ERROR: --target requires a value"; exit 2; }
		shift 2
		;;
	--tag)
		IMAGE_TAG="${2:-}"
		[[ -n "${IMAGE_TAG}" ]] || { echo "ERROR: --tag requires a value"; exit 2; }
		shift 2
		;;
	--push)
		PUSH=1
		shift
		;;
	--publish)
		PUBLISH=1
		PUSH=1
		shift
		;;
	--registry)
		REGISTRY="${2:-}"
		[[ -n "${REGISTRY}" ]] || { echo "ERROR: --registry requires a value"; exit 2; }
		shift 2
		;;
	--owner)
		OWNER="${2:-}"
		[[ -n "${OWNER}" ]] || { echo "ERROR: --owner requires a value"; exit 2; }
		shift 2
		;;
	--repo-prefix)
		REPO_PREFIX="${2:-}"
		[[ -n "${REPO_PREFIX}" ]] || { echo "ERROR: --repo-prefix requires a value"; exit 2; }
		shift 2
		;;
	--version)
		VERSION="${2:-}"
		[[ -n "${VERSION}" ]] || { echo "ERROR: --version requires a value"; exit 2; }
		shift 2
		;;
	--stable)
		IS_STABLE="${2:-}"
		[[ -n "${IS_STABLE}" ]] || { echo "ERROR: --stable requires a value (true|false)"; exit 2; }
		shift 2
		;;
	-h|--help)
		usage
		exit 0
		;;
	*)
		echo "ERROR: Unknown argument: $1" >&2
		usage
		exit 2
		;;
	esac
done

# Derive default TARGET from VARIANT if not explicitly provided
if [[ -z "${TARGET}" ]]; then
	if [[ "${VARIANT}" == "slim" ]]; then
		TARGET="slim"
	else
		TARGET="full"
	fi
fi

# Derive default local tag if not provided
if [[ -z "${IMAGE_TAG}" ]]; then
	IMAGE_TAG="${REPO_PREFIX}-${INFINITO_DISTRO}"
	if [[ "${VARIANT}" == "slim" ]]; then
		IMAGE_TAG="${IMAGE_TAG}-slim"
	fi
fi

# Compute PKGMGR_IMAGE based on variant (slim uses pkgmgr-*-slim)
if [[ "${VARIANT}" == "slim" ]]; then
	PKGMGR_IMAGE="ghcr.io/${PKGMGR_IMAGE_OWNER}/pkgmgr-${INFINITO_DISTRO}-slim:${PKGMGR_IMAGE_TAG}"
else
	PKGMGR_IMAGE="ghcr.io/${PKGMGR_IMAGE_OWNER}/pkgmgr-${INFINITO_DISTRO}:${PKGMGR_IMAGE_TAG}"
fi

# Local-only "missing" shortcut
if [[ "${MISSING_ONLY}" == "1" ]]; then
	if [[ "${PUSH}" == "1" ]]; then
		echo "ERROR: --missing is only supported for local builds (without --push/--publish)" >&2
		exit 2
	fi
	if docker image inspect "${IMAGE_TAG}" >/dev/null 2>&1; then
		echo "[build] Image already exists: ${IMAGE_TAG} (skipping due to --missing)"
		exit 0
	fi
fi

# Validate publish parameters
if [[ "${PUBLISH}" == "1" ]]; then
	[[ -n "${REGISTRY}" ]] || { echo "ERROR: --publish requires --registry"; exit 2; }
	[[ -n "${OWNER}" ]] || { echo "ERROR: --publish requires --owner"; exit 2; }
	[[ -n "${VERSION}" ]] || { echo "ERROR: --publish requires --version"; exit 2; }
fi

# Guard: --push without --publish requires fully-qualified --tag
if [[ "${PUSH}" == "1" && "${PUBLISH}" != "1" ]]; then
	if [[ "${IMAGE_TAG}" != */* ]]; then
		echo "ERROR: --push requires --tag with a fully-qualified name (e.g. ghcr.io/<owner>/<image>:tag), or use --publish" >&2
		exit 2
	fi
fi

echo
echo "------------------------------------------------------------"
echo "[build] Building image"
echo "distro               = ${INFINITO_DISTRO}"
echo "variant              = ${VARIANT}"
echo "target               = ${TARGET}"
echo "PKGMGR_IMAGE          = ${PKGMGR_IMAGE}"
if [[ "${NO_CACHE}" == "1" ]]; then echo "cache               = disabled"; fi
if [[ "${PUSH}" == "1" ]]; then echo "push                = enabled"; fi
if [[ "${PUBLISH}" == "1" ]]; then
	echo "publish             = enabled"
	echo "registry            = ${REGISTRY}"
	echo "owner               = ${OWNER}"
	echo "version             = ${VERSION}"
	echo "stable              = ${IS_STABLE}"
fi
if [[ -n "${NIX_CONFIG:-}" ]]; then
	echo "NIX_CONFIG           = <set>"
else
	echo "NIX_CONFIG           = <empty>"
fi
echo "------------------------------------------------------------"

# Common build args
build_args=(
	--build-arg "PKGMGR_IMAGE=${PKGMGR_IMAGE}"
	--build-arg "NIX_CONFIG=${NIX_CONFIG:-}"
)

if [[ "${NO_CACHE}" == "1" ]]; then
	build_args+=(--no-cache)
fi

if [[ -n "${TARGET}" ]]; then
	build_args+=(--target "${TARGET}")
fi

compute_publish_tags() {
	local suffix=""
	local distro_tag_base=""
	local alias_tag_base=""

	if [[ "${VARIANT}" == "slim" ]]; then
		suffix="-slim"
	fi

	distro_tag_base="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${INFINITO_DISTRO}${suffix}"

	if [[ "${INFINITO_DISTRO}" == "${DEFAULT_DISTRO}" ]]; then
		alias_tag_base="${REGISTRY}/${OWNER}/${REPO_PREFIX}${suffix}"
	fi

	local tags=()
	tags+=("${distro_tag_base}:latest")
	tags+=("${distro_tag_base}:${VERSION}")

	if [[ "${IS_STABLE}" == "true" ]]; then
		tags+=("${distro_tag_base}:stable")
	fi

	if [[ -n "${alias_tag_base}" ]]; then
		tags+=("${alias_tag_base}:latest")
		tags+=("${alias_tag_base}:${VERSION}")
		if [[ "${IS_STABLE}" == "true" ]]; then
			tags+=("${alias_tag_base}:stable")
		fi
	fi

	printf '%s\n' "${tags[@]}"
}

if [[ "${PUSH}" == "1" ]]; then
	bx_args=(docker buildx build --push)

	if [[ "${PUBLISH}" == "1" ]]; then
		while IFS= read -r t; do
			bx_args+=(-t "$t")
		done < <(compute_publish_tags)
	else
		bx_args+=(-t "${IMAGE_TAG}")
	fi

	bx_args+=("${build_args[@]}")
	bx_args+=(.)

	echo "[build] Running: ${bx_args[*]}"
	"${bx_args[@]}"
else
	local_args=(docker build)
	local_args+=("${build_args[@]}")
	local_args+=(-t "${IMAGE_TAG}")
	local_args+=(.)

	echo "[build] Running: ${local_args[*]}"
	"${local_args[@]}"
fi
