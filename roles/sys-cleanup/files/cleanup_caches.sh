#!/usr/bin/env bash
# Cross-distro CI/container cleanup: package-manager and language-tool caches.
set -euo pipefail

echo "=== [cleanup] package manager caches ==="
if command -v apt-get >/dev/null 2>&1; then
  apt-get clean || true
fi

if command -v pacman >/dev/null 2>&1; then
  pacman -Scc --noconfirm || true
fi

if command -v dnf >/dev/null 2>&1; then
  dnf clean all || true
  rm -rf /var/cache/dnf || true
fi

if command -v yum >/dev/null 2>&1; then
  yum clean all || true
  rm -rf /var/cache/yum || true
fi

echo "=== [cleanup] language/tool caches (best effort) ==="
rm -rf /root/.cache/pip /home/*/.cache/pip 2>/dev/null || true
rm -rf /root/.npm /home/*/.npm 2>/dev/null || true
rm -rf /root/.cache/yarn /home/*/.cache/yarn 2>/dev/null || true
rm -rf /root/.cache/go-build /home/*/.cache/go-build 2>/dev/null || true
