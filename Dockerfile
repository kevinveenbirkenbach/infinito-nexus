# syntax=docker/dockerfile:1

ARG PKGMGR_IMAGE_REPO=ghcr.io/kevinveenbirkenbach/pkgmgr-arch
ARG PKGMGR_IMAGE_TAG=stable

FROM ${PKGMGR_IMAGE_REPO}:${PKGMGR_IMAGE_TAG} AS full

# Hadolint DL4006: ensure pipefail is set for RUN instructions that use pipes
SHELL ["/bin/bash", "-o", "pipefail", "-lc"]

# Forwardable build-time Nix settings (e.g., GitHub access tokens to avoid rate limits)
ARG NIX_CONFIG

# Make Nix non-interactive by default, but allow override/extension via build arg
ENV NIX_CONFIG="${NIX_CONFIG:+$NIX_CONFIG }accept-flake-config = true"

ENV INFINITO_SRC_DIR="/opt/src/infinito"
ENV PYTHON="/opt/venvs/infinito/bin/python"
ENV PIP="/opt/venvs/infinito/bin/python -m pip"
ENV PATH="/opt/venvs/infinito/bin:${PATH}"

RUN cat /etc/os-release || true

# ------------------------------------------------------------
# Infinito.Nexus source in
# ------------------------------------------------------------
COPY . ${INFINITO_SRC_DIR}

# ------------------------------------------------------------
# Install Docker CLI (client only) - distro aware
# ------------------------------------------------------------
# hadolint ignore=DL3008,DL3041
RUN /bin/bash ${INFINITO_SRC_DIR}/roles/sys-svc-docker/files/install-cli.sh

# ------------------------------------------------------------
# Install systemd + dbus (for CI Ansible systemd/service tests)
# ------------------------------------------------------------

# hadolint ignore=DL3008,DL3033,DL3041
RUN set -euo pipefail; \
  . /etc/os-release; \
  echo "[docker-infinito] Installing systemd/dbus for ID=${ID}"; \
  case "${ID}" in \
    arch) \
      pacman -Syu --noconfirm --needed systemd dbus; \
      ;; \
    debian|ubuntu) \
      apt-get update; \
      apt-get install -y --no-install-recommends systemd systemd-sysv dbus; \
      rm -rf /var/lib/apt/lists/*; \
      ;; \
    fedora) \
      dnf -y install systemd dbus; \
      dnf -y clean all; \
      ;; \
    centos|rhel) \
      (command -v dnf >/dev/null 2>&1 && dnf -y install systemd dbus && dnf -y clean all) || \
      (yum -y install systemd dbus && yum -y clean all); \
      ;; \
    *) \
      echo "[WARN] Unknown distro ID=${ID}. Skipping systemd install."; \
      ;; \
  esac

# ------------------------------------------------------------
# Disable interactive first-boot units (CI / container safe)
# ------------------------------------------------------------
RUN set -euo pipefail; \
  systemctl mask systemd-firstboot.service first-boot-complete.target || true; \
  systemd-machine-id-setup || true


# systemd-in-container conventions
ENV container=docker
STOPSIGNAL SIGRTMIN+3

# ------------------------------------------------------------
# Install infinito via pkgmgr (shallow)
# ------------------------------------------------------------
RUN set -euo pipefail; \
  export NIX_CONFIG="${NIX_CONFIG:-}"; \
  echo "[docker-infinito] Install Infinito.Nexus via pkgmgr"; \
  pkgmgr install infinito --clone-mode shallow; \
  echo "[docker-infinito] Installed Infinito.Nexus Version:"; \
  pkgmgr version infinito

# ------------------------------------------------------------
# Override with local source (during build)
# ------------------------------------------------------------
RUN set -euo pipefail; \
  export NIX_CONFIG="${NIX_CONFIG:-}"; \
  INSTALL_LOCAL_BUILD=1 /opt/src/infinito/scripts/docker/entry.sh true

# Set workdir to / to avoid ambiguous commands
WORKDIR /

COPY scripts/docker/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

ENTRYPOINT ["/opt/src/infinito/scripts/docker/entry.sh"]
HEALTHCHECK --interval=5s --timeout=5s --start-period=30s --retries=20 \
  CMD /usr/local/bin/healthcheck.sh

# IMPORTANT: default to systemd as PID 1
CMD ["/sbin/init"]
