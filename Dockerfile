# ------------------------------------------------------------
# Infinito dev container (multi-distro)
# ------------------------------------------------------------
ARG BASE_IMAGE=archlinux:latest
FROM ${BASE_IMAGE}

# ------------------------------------------------------------
# Base dependencies per distro
# - git, python, venv tooling
# - docker CLI (best-effort)
# - rsync, build tools, CA certificates
# ------------------------------------------------------------
RUN set -e; \
    if [ -f /etc/os-release ]; then \
      . /etc/os-release; \
    else \
      echo "ERROR: /etc/os-release not found, cannot detect distro."; \
      exit 1; \
    fi; \
    echo "[infinito] Detected base distro: ${ID:-unknown}"; \
    case "${ID}" in \
      arch) \
        pacman -Syu --noconfirm \
          base-devel \
          git \
          python \
          python-pip \
          python-setuptools \
          rsync \
          alsa-lib \
          go \
          docker \
          curl \
          ca-certificates; \
        pacman -Scc --noconfirm; \
        # Ensure python3 exists (Arch only ships 'python' by default) \
        if [ ! -x /usr/bin/python3 ]; then \
          ln -sf /usr/bin/python /usr/bin/python3; \
        fi; \
        # Stub systemctl and yay to avoid side effects in containers \
        printf '#!/bin/sh\nexit 0\n' > /usr/bin/systemctl; \
        chmod +x /usr/bin/systemctl; \
        printf '#!/bin/sh\nexit 0\n' > /usr/bin/yay; \
        chmod +x /usr/bin/yay; \
        ;; \
      debian|ubuntu) \
        apt-get update; \
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
          build-essential \
          git \
          python3 \
          python3-venv \
          python3-pip \
          python3-setuptools \
          rsync \
          libasound2 \
          docker.io \
          curl \
          ca-certificates; \
        rm -rf /var/lib/apt/lists/*; \
        ;; \
      fedora|rhel|centos) \
        dnf -y update; \
        dnf -y install \
          git \
          python3 \
          python3-pip \
          python3-setuptools \
          make \
          gcc \
          rsync \
          alsa-lib \
          docker \
          curl \
          ca-certificates \
          xz; \
        dnf clean all; \
        ;; \
      *) \
        echo "ERROR: Unsupported base distro '${ID}'."; \
        exit 1; \
        ;; \
    esac

# ------------------------------------------------------------
# pkgmgr via Python venv (distro-agnostic)
# ------------------------------------------------------------
ENV PKGMGR_REPO=/opt/package-manager \
    PKGMGR_VENV=/root/.venvs/pkgmgr

RUN git clone https://github.com/kevinveenbirkenbach/package-manager.git "$PKGMGR_REPO" \
 && python3 -m venv "$PKGMGR_VENV" \
 && "$PKGMGR_VENV/bin/pip" install --upgrade pip \
 && "$PKGMGR_VENV/bin/pip" install --no-cache-dir \
      -r "$PKGMGR_REPO/requirements.txt" \
      ansible \
      simpleaudio \
 && printf '#!/bin/sh\n. %s/bin/activate\nexec python %s/main.py "$@"\n' \
           "$PKGMGR_VENV" "$PKGMGR_REPO" > /usr/local/bin/pkgmgr \
 && chmod +x /usr/local/bin/pkgmgr

ENV PATH="$PKGMGR_VENV/bin:/root/.local/bin:${PATH}"

# ------------------------------------------------------------
# Copy local Infinito source into the image
# ------------------------------------------------------------
COPY . /opt/infinito-src

# ------------------------------------------------------------
# Install Infinito via pkgmgr (shallow clone)
# ------------------------------------------------------------
RUN pkgmgr install infinito --clone-mode shallow

# ------------------------------------------------------------
# Override installed Infinito with local source
# (keeps pkgmgr metadata, but code comes from /opt/infinito-src)
# ------------------------------------------------------------
RUN INFINITO_PATH="$(pkgmgr path infinito)" && \
    rm -rf "${INFINITO_PATH:?}"/* && \
    rsync -a --delete --exclude='.git' /opt/infinito-src/ "${INFINITO_PATH}/"

# ------------------------------------------------------------
# Symlink infinito CLI into PATH
# ------------------------------------------------------------
RUN INFINITO_PATH="$(pkgmgr path infinito)" && \
    ln -sf "${INFINITO_PATH}/main.py" /usr/local/bin/infinito && \
    chmod +x /usr/local/bin/infinito

# ------------------------------------------------------------
# Default command: show help and keep container running
# ------------------------------------------------------------
CMD sh -c "infinito --help && exec tail -f /dev/null"
