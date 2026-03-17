#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PLAYWRIGHT_IMAGE="${PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright:v1.50.1-noble}"
PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION:-1.50.1}"
PLAYWRIGHT_CODEGEN_BROWSER="${PLAYWRIGHT_CODEGEN_BROWSER:-firefox}"

CONTAINER_RUNTIME=()
CONTAINER_ARGS=()

detect_container_runtime() {
  if command -v container >/dev/null 2>&1; then
    CONTAINER_RUNTIME=(container run)
    return
  fi

  if command -v docker >/dev/null 2>&1; then
    CONTAINER_RUNTIME=(docker run)
    return
  fi

  if command -v podman >/dev/null 2>&1; then
    CONTAINER_RUNTIME=(podman run)
    return
  fi

  echo "No supported container runtime found."
  echo "Install 'container', 'docker', or 'podman' to use Playwright recording."
  exit 1
}

append_display_args() {
  if [[ -n "${DISPLAY:-}" ]] && [[ -d /tmp/.X11-unix ]]; then
    CONTAINER_ARGS+=(-e "DISPLAY=${DISPLAY}")
    CONTAINER_ARGS+=(-v /tmp/.X11-unix:/tmp/.X11-unix:rw)
    if [[ -n "${XAUTHORITY:-}" ]] && [[ -f "${XAUTHORITY}" ]]; then
      CONTAINER_ARGS+=(-e XAUTHORITY=/tmp/.Xauthority)
      CONTAINER_ARGS+=(-v "${XAUTHORITY}:/tmp/.Xauthority:ro")
    fi
    return
  fi

  if [[ -n "${WAYLAND_DISPLAY:-}" ]] && [[ -n "${XDG_RUNTIME_DIR:-}" ]]; then
    local wayland_socket="${XDG_RUNTIME_DIR}/${WAYLAND_DISPLAY}"
    if [[ -S "${wayland_socket}" ]]; then
      CONTAINER_ARGS+=(-e "WAYLAND_DISPLAY=${WAYLAND_DISPLAY}")
      CONTAINER_ARGS+=(-e XDG_RUNTIME_DIR=/tmp/xdg-runtime)
      CONTAINER_ARGS+=(-v "${XDG_RUNTIME_DIR}:/tmp/xdg-runtime")
      return
    fi
  fi
}

cd "${PROJECT_DIR}"

if [[ $# -eq 0 ]] || [[ "$1" == -* ]]; then
  echo "URL is required as the first argument."
  echo "Example: ./scripts/record.sh https://dashboard.infinito.example"
  exit 1
fi

TARGET_URL="$1"
shift
EXTRA_ARGS=("$@")
DEFAULT_OUTPUT_FILE="volume/codegen.spec.js"
HAS_OUTPUT_FLAG=0
HAS_BROWSER_FLAG=0

for arg in "${EXTRA_ARGS[@]}"; do
  case "${arg}" in
    -o|--output|-o=*|--output=*)
      HAS_OUTPUT_FLAG=1
      ;;
    -b|--browser|-b=*|--browser=*)
      HAS_BROWSER_FLAG=1
      ;;
  esac
done

if [[ ${HAS_OUTPUT_FLAG} -eq 0 ]]; then
  EXTRA_ARGS=(-o "${DEFAULT_OUTPUT_FILE}" "${EXTRA_ARGS[@]}")
  echo "Recording to ${PROJECT_DIR}/${DEFAULT_OUTPUT_FILE}"
fi

if [[ ${HAS_BROWSER_FLAG} -eq 0 ]]; then
  EXTRA_ARGS=(--browser "${PLAYWRIGHT_CODEGEN_BROWSER}" "${EXTRA_ARGS[@]}")
  echo "Using Playwright browser ${PLAYWRIGHT_CODEGEN_BROWSER}"
fi

if [[ -z "${DISPLAY:-}" ]] && [[ -z "${WAYLAND_DISPLAY:-}" ]]; then
  echo "No graphical session detected."
  echo "Set DISPLAY or WAYLAND_DISPLAY before starting Playwright recording."
  exit 1
fi

detect_container_runtime

mkdir -p "${PROJECT_DIR}/volume/home" "${PROJECT_DIR}/volume/npm-cache"

CONTAINER_ARGS+=(
  --rm
  --init
  --ipc=host
  --shm-size=1g
  --cap-add=SYS_ADMIN
  --network host
  --user "$(id -u):$(id -g)"
  -e HOME=/work/volume/home
  -e PW_CODEGEN_NO_INSPECTOR=1
  -e npm_config_cache=/work/volume/npm-cache
  -v "${PROJECT_DIR}:/work"
  -w /work
)

if [[ -f /etc/hosts ]]; then
  CONTAINER_ARGS+=(-v /etc/hosts:/etc/hosts:ro)
fi

if [[ -f /etc/resolv.conf ]]; then
  CONTAINER_ARGS+=(-v /etc/resolv.conf:/etc/resolv.conf:ro)
fi

append_display_args

exec "${CONTAINER_RUNTIME[@]}" \
  "${CONTAINER_ARGS[@]}" \
  "${PLAYWRIGHT_IMAGE}" \
  /bin/bash \
  -lc \
  "mkdir -p \"\$HOME\" \"\$npm_config_cache\" && exec npx --yes playwright@${PLAYWRIGHT_VERSION} codegen --ignore-https-errors \"\$1\" \"\${@:2}\"" \
  playwright-codegen \
  "${TARGET_URL}" \
  "${EXTRA_ARGS[@]}"
