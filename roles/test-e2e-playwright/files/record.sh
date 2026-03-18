#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}"
PLAYWRIGHT_PACKAGE_JSON="${PROJECT_DIR}/package.json"
PLAYWRIGHT_IMAGE="${PLAYWRIGHT_IMAGE:-}"
PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION:-}"
PLAYWRIGHT_IMAGE_DISTRO="${PLAYWRIGHT_IMAGE_DISTRO:-noble}"
PLAYWRIGHT_CODEGEN_BROWSER="${PLAYWRIGHT_CODEGEN_BROWSER:-firefox}"
REPO_ROOT=""
PROJECT_RELATIVE_DIR=""
PROJECT_ROLE=""
TARGET_ROLE="${ROLE:-}"
TARGET_URL="${URL:-}"

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

detect_playwright_version() {
  local version

  if [[ -n "${PLAYWRIGHT_VERSION}" ]]; then
    return
  fi

  if [[ ! -f "${PLAYWRIGHT_PACKAGE_JSON}" ]]; then
    echo "Could not find ${PLAYWRIGHT_PACKAGE_JSON}."
    exit 1
  fi

  version="$(sed -nE 's/.*"@playwright\/test"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/p' "${PLAYWRIGHT_PACKAGE_JSON}" | head -n 1)"
  version="$(printf '%s' "${version}" | sed -E 's/^[^0-9]*//')"

  if [[ -z "${version}" ]]; then
    echo "Could not determine @playwright/test version from ${PLAYWRIGHT_PACKAGE_JSON}."
    exit 1
  fi

  PLAYWRIGHT_VERSION="${version}"
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

find_repo_root() {
  local current_dir="${PROJECT_DIR}"

  while [[ "${current_dir}" != "/" ]]; do
    if [[ -e "${current_dir}/.git" ]]; then
      REPO_ROOT="${current_dir}"
      return
    fi
    current_dir="$(dirname "${current_dir}")"
  done

  echo "Could not locate the repository root from ${PROJECT_DIR}."
  exit 1
}

detect_project_context() {
  local role_relative_path
  local role_name
  local role_suffix

  PROJECT_RELATIVE_DIR="${PROJECT_DIR#"${REPO_ROOT}"/}"
  if [[ "${PROJECT_RELATIVE_DIR}" == "${PROJECT_DIR}" ]]; then
    echo "Project directory ${PROJECT_DIR} is not inside repository ${REPO_ROOT}."
    exit 1
  fi

  role_relative_path="${PROJECT_DIR#"${REPO_ROOT}"/roles/}"
  if [[ "${role_relative_path}" == "${PROJECT_DIR}" ]]; then
    return
  fi

  role_name="${role_relative_path%%/*}"
  role_suffix="${role_relative_path#"${role_name}"/}"
  if [[ "${role_suffix}" == "tests/playwright" ]]; then
    PROJECT_ROLE="${role_name}"
  fi
}

show_known_roles() {
  local role_dir
  local role_name

  echo "Known roles:"
  for role_dir in "${REPO_ROOT}"/roles/*; do
    [[ -d "${role_dir}" ]] || continue
    role_name="$(basename "${role_dir}")"
    echo " - ${role_name}"
  done
}

prompt_for_role() {
  while [[ -z "${TARGET_ROLE}" ]]; do
    read -r -p "Role name: " TARGET_ROLE
    if [[ -z "${TARGET_ROLE}" ]]; then
      echo "Role name is required."
      continue
    fi

    if [[ -d "${REPO_ROOT}/roles/${TARGET_ROLE}" ]]; then
      return
    fi

    echo "Role '${TARGET_ROLE}' does not exist under ${REPO_ROOT}/roles."
    show_known_roles
    TARGET_ROLE=""
  done
}

prompt_for_url() {
  while [[ -z "${TARGET_URL}" ]]; do
    read -r -p "Target URL: " TARGET_URL
    if [[ -z "${TARGET_URL}" ]]; then
      echo "A target URL is required."
    fi
  done
}

cd "${PROJECT_DIR}"
find_repo_root
detect_project_context

if [[ $# -gt 0 ]] && [[ "$1" != -* ]]; then
  TARGET_URL="$1"
  shift
fi

EXTRA_ARGS=("$@")
DEFAULT_OUTPUT_FILE=""
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

if [[ -z "${TARGET_ROLE}" && -n "${PROJECT_ROLE}" ]]; then
  TARGET_ROLE="${PROJECT_ROLE}"
  echo "Using role ${TARGET_ROLE} from the current script location."
fi

if [[ -n "${TARGET_ROLE}" ]] && [[ ! -d "${REPO_ROOT}/roles/${TARGET_ROLE}" ]]; then
  echo "Role '${TARGET_ROLE}' does not exist under ${REPO_ROOT}/roles."
  exit 1
fi

if [[ ${HAS_OUTPUT_FLAG} -eq 0 ]]; then
  if [[ -z "${TARGET_ROLE}" ]]; then
    prompt_for_role
  fi

  mkdir -p "${REPO_ROOT}/roles/${TARGET_ROLE}/files"
  DEFAULT_OUTPUT_FILE="/work/roles/${TARGET_ROLE}/files/playwright.spec.js"
  EXTRA_ARGS=(-o "${DEFAULT_OUTPUT_FILE}" "${EXTRA_ARGS[@]}")
  echo "Recording to ${REPO_ROOT}/roles/${TARGET_ROLE}/files/playwright.spec.js"
fi

prompt_for_url

if [[ ${HAS_BROWSER_FLAG} -eq 0 ]]; then
  EXTRA_ARGS=(--browser "${PLAYWRIGHT_CODEGEN_BROWSER}" "${EXTRA_ARGS[@]}")
  echo "Using Playwright browser ${PLAYWRIGHT_CODEGEN_BROWSER}"
fi

if [[ -z "${DISPLAY:-}" ]] && [[ -z "${WAYLAND_DISPLAY:-}" ]]; then
  echo "No graphical session detected."
  echo "Set DISPLAY or WAYLAND_DISPLAY before starting Playwright recording."
  exit 1
fi

detect_playwright_version

if [[ -z "${PLAYWRIGHT_IMAGE}" ]]; then
  PLAYWRIGHT_IMAGE="mcr.microsoft.com/playwright:v${PLAYWRIGHT_VERSION}-${PLAYWRIGHT_IMAGE_DISTRO}"
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
  -e "HOME=/work/${PROJECT_RELATIVE_DIR}/volume/home"
  -e PW_CODEGEN_NO_INSPECTOR=1
  -e "npm_config_cache=/work/${PROJECT_RELATIVE_DIR}/volume/npm-cache"
  -v "${REPO_ROOT}:/work"
  -w "/work/${PROJECT_RELATIVE_DIR}"
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
  "mkdir -p \"\$HOME\" \"\$npm_config_cache\" && exec npx --yes playwright@${PLAYWRIGHT_VERSION} codegen --ignore-https-errors \"\${@:2}\" \"\$1\"" \
  playwright-codegen \
  "${TARGET_URL}" \
  "${EXTRA_ARGS[@]}"
