#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f /etc/os-release ]]; then
  echo "[ERROR] /etc/os-release not found; unsupported system." >&2
  exit 1
fi

# shellcheck disable=SC1091
. /etc/os-release
ID_LIKE="${ID_LIKE:-}"

log() {
  printf '>>> [dev-python] %s\n' "$*"
}

install_python_packages() {
  case "${ID}" in
    arch)
      pacman -Syu --noconfirm --needed python python-pip
      pacman -Scc --noconfirm || true
      ;;

    debian | ubuntu)
      export DEBIAN_FRONTEND=noninteractive
      apt-get update
      apt-get install -y --no-install-recommends python3 python3-pip
      for v in 3.13 3.12 3.11; do
        if apt-cache show "python${v}" >/dev/null 2>&1; then
          apt-get install -y --no-install-recommends "python${v}" || true
          if apt-cache show "python${v}-venv" >/dev/null 2>&1; then
            apt-get install -y --no-install-recommends "python${v}-venv" || true
          fi
          break
        fi
      done
      rm -rf /var/lib/apt/lists/*
      ;;

    fedora)
      dnf -y install python3 python3-pip
      dnf -y install python3.11 python3.11-pip || true
      dnf -y clean all || true
      rm -rf /var/cache/dnf || true
      ;;

    centos | rhel)
      if command -v dnf >/dev/null 2>&1; then
        PM=dnf
      else
        PM=yum
      fi
      ${PM} -y install python3 python3-pip || true
      ${PM} -y install python3.11 python3.11-pip || true
      ${PM} -y clean all || true
      rm -rf "/var/cache/${PM}" || true
      ;;

    *)
      if [[ "${ID_LIKE}" =~ (rhel|centos) ]]; then
        if command -v dnf >/dev/null 2>&1; then
          PM=dnf
        else
          PM=yum
        fi
        ${PM} -y install python3 python3-pip || true
        ${PM} -y install python3.11 python3.11-pip || true
        ${PM} -y clean all || true
        rm -rf "/var/cache/${PM}" || true
      else
        echo "[ERROR] Unsupported distro for Python install: ID=${ID} ID_LIKE=${ID_LIKE}" >&2
        exit 1
      fi
      ;;
  esac
}

python_is_311_or_higher() {
  local bin="$1"
  "${bin}" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
}

pick_python_bin() {
  local bin
  for bin in \
    /usr/bin/python3.15 \
    /usr/bin/python3.14 \
    /usr/bin/python3.13 \
    /usr/bin/python3.12 \
    /usr/bin/python3.11 \
    /usr/bin/python3.10 \
    /usr/bin/python3; do
    [[ -x "${bin}" ]] || continue
    if python_is_311_or_higher "${bin}"; then
      printf '%s\n' "${bin}"
      return 0
    fi
  done
  return 1
}

configure_defaults() {
  local pybin="$1"
  local pyver
  local versioned_pip

  pyver="$("${pybin}" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
  versioned_pip="/usr/bin/pip${pyver}"

  install -d /usr/local/bin
  ln -sfn "${pybin}" /usr/local/bin/python3
  ln -sfn /usr/local/bin/python3 /usr/local/bin/python

  if [[ -x "${versioned_pip}" ]]; then
    ln -sfn "${versioned_pip}" /usr/local/bin/pip3
  else
    if ! "${pybin}" -m pip --version >/dev/null 2>&1; then
      "${pybin}" -m ensurepip --upgrade >/dev/null 2>&1 || true
    fi
    if "${pybin}" -m pip --version >/dev/null 2>&1; then
      cat >/usr/local/bin/pip3 <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec /usr/local/bin/python3 -m pip "$@"
EOF
      chmod 0755 /usr/local/bin/pip3
    elif [[ -x /usr/bin/pip3 ]] && /usr/bin/pip3 --version 2>/dev/null | grep -q "python ${pyver}"; then
      ln -sfn /usr/bin/pip3 /usr/local/bin/pip3
    else
      echo "[ERROR] Could not provide pip3 for Python ${pyver}." >&2
      exit 1
    fi
  fi

  ln -sfn /usr/local/bin/pip3 /usr/local/bin/pip
}

log "Installing Python packages for ID=${ID} ID_LIKE=${ID_LIKE}"
install_python_packages

if ! PYBIN="$(pick_python_bin)"; then
  echo "[ERROR] No Python >= 3.11 found after installation attempt." >&2
  if command -v python3 >/dev/null 2>&1; then
    python3 --version || true
  fi
  exit 1
fi

configure_defaults "${PYBIN}"

log "Default python: $(python3 --version)"
log "Default pip: $(pip3 --version)"
