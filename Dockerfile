# syntax=docker/dockerfile:1

# Base image (pkgmgr) selector
# Example:
#   PKGMGR_IMAGE=ghcr.io/kevinveenbirkenbach/pkgmgr-arch:stable
#   PKGMGR_IMAGE=ghcr.io/kevinveenbirkenbach/pkgmgr-arch-slim:stable
ARG PKGMGR_IMAGE=ghcr.io/kevinveenbirkenbach/pkgmgr-arch:stable
FROM ${PKGMGR_IMAGE} AS full

# Hadolint DL4006: ensure pipefail is set for RUN instructions that use pipes
SHELL ["/bin/bash", "-o", "pipefail", "-lc"]

# Forwardable build-time Nix settings (e.g., GitHub access tokens to avoid rate limits)
ARG NIX_CONFIG

ENV INFINITO_SRC_DIR="/opt/src/infinito"
ENV PYTHON="/opt/venvs/infinito/bin/python"
ENV PIP="/opt/venvs/infinito/bin/python -m pip"
ENV PATH="/opt/venvs/infinito/bin:${PATH}"

# Make Nix non-interactive for flake config (CI-friendly)
RUN set -euo pipefail; \
  cat /etc/os-release || true; \
  if [ -f /etc/nix/nix.conf ]; then \
    grep -q '^accept-flake-config *= *true' /etc/nix/nix.conf || \
    echo 'accept-flake-config = true' >> /etc/nix/nix.conf; \
  fi

# ------------------------------------------------------------
# Infinito.Nexus source in
# ------------------------------------------------------------
COPY . ${INFINITO_SRC_DIR}

# ------------------------------------------------------------
# Prepare Python, Docker CLI, and system services needed for CI/builds
# ------------------------------------------------------------
# hadolint ignore=DL3008,DL3033,DL3041
RUN set -euo pipefail; \
  /bin/bash ${INFINITO_SRC_DIR}/roles/dev-python/files/install.sh; \
  /bin/bash ${INFINITO_SRC_DIR}/roles/sys-svc-container/files/install-cli.sh; \
  . /etc/os-release; \
  echo "[docker-infinito] Installing systemd/dbus + ssh client for ID=${ID}"; \
  case "${ID}" in \
    arch) \
      pacman -Syu --noconfirm --needed systemd dbus openssh; \
      ;; \
    debian|ubuntu) \
      apt-get update; \
      apt-get install -y --no-install-recommends \
        systemd systemd-sysv dbus \
        openssh-client; \
      rm -rf /var/lib/apt/lists/*; \
      ;; \
    fedora) \
      dnf -y install systemd dbus openssh-clients; \
      dnf -y clean all; \
      ;; \
    centos|rhel) \
      (command -v dnf >/dev/null 2>&1 && dnf -y install systemd dbus openssh-clients && dnf -y clean all) || \
      (yum -y install systemd dbus openssh-clients && yum -y clean all); \
      ;; \
    *) \
      echo "[WARN] Unknown distro ID=${ID}. Skipping systemd/dbus/ssh install."; \
      ;; \
  esac; \
  systemctl mask systemd-firstboot.service first-boot-complete.target || true; \
  systemd-machine-id-setup || true

# systemd-in-container conventions
ENV container=docker
STOPSIGNAL SIGRTMIN+3

# ------------------------------------------------------------
# Install infinito via pkgmgr (shallow) and override it with local source
# ------------------------------------------------------------
RUN set -euo pipefail; \
  export NIX_CONFIG="${NIX_CONFIG:-}"; \
  echo "[docker-infinito] Install Infinito.Nexus via pkgmgr"; \
  pkgmgr install infinito --clone-mode shallow; \
  echo "[docker-infinito] Installed Infinito.Nexus Version:"; \
  pkgmgr version infinito; \
  INFINITO_COMPILE=1 /opt/src/infinito/scripts/docker/entry.sh true

# Set workdir to / to avoid ambiguous commands
WORKDIR /

COPY scripts/docker/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh
HEALTHCHECK --interval=5s --timeout=5s --start-period=30s --retries=20 \
  CMD /usr/local/bin/healthcheck.sh

ENTRYPOINT ["/opt/src/infinito/scripts/docker/entry.sh"]

# IMPORTANT: default to systemd as PID 1
CMD ["/sbin/init"]


# ============================================================
# Target: slim
# - based on full, runs slim.sh
# ============================================================
FROM full AS slim

# Image cleanup (reduce final size)
RUN set -euo pipefail; \
  test -x /usr/local/bin/slim.sh || { echo "slim.sh missing in base image" >&2; exit 1; }; \
  /usr/local/bin/slim.sh
