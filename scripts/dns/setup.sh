#!/usr/bin/env bash
set -euo pipefail

DOMAIN="infinito.example"

NM_CONF="/etc/NetworkManager/conf.d/00-infinito-dnsmasq.conf"
NM_DNSMASQ_DIR="/etc/NetworkManager/dnsmasq.d"
NM_DNSMASQ_CONF="${NM_DNSMASQ_DIR}/${DOMAIN}.conf"

SYS_DNSMASQ_CONF="/etc/dnsmasq.d/${DOMAIN}.conf"

echo ">>> Setting up local DNS for *.${DOMAIN} -> 127.0.0.1"

install_dnsmasq_if_missing() {
  if command -v dnsmasq >/dev/null 2>&1; then
    return 0
  fi

  echo ">>> dnsmasq not found -> installing"

  if command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --noconfirm --needed dnsmasq
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y dnsmasq
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y dnsmasq
  else
    echo "ERROR: Unsupported distro/package manager. Install dnsmasq manually."
    exit 1
  fi
}

configure_via_networkmanager_dnsmasq() {
  echo ">>> Detected NetworkManager -> configuring NM dnsmasq plugin (recommended)"
  install_dnsmasq_if_missing

  # Avoid port conflicts with a system-wide dnsmasq service
  if systemctl is-enabled --quiet dnsmasq 2>/dev/null || systemctl is-active --quiet dnsmasq 2>/dev/null; then
    echo ">>> Disabling system dnsmasq to avoid conflicts with NetworkManager dnsmasq"
    sudo systemctl disable --now dnsmasq || true
  fi

  echo ">>> Writing NetworkManager dnsmasq config: ${NM_CONF}"
  sudo mkdir -p "$(dirname "${NM_CONF}")"
  cat <<EOF | sudo tee "${NM_CONF}" >/dev/null
[main]
dns=dnsmasq
EOF

  echo ">>> Writing dnsmasq snippet for NetworkManager: ${NM_DNSMASQ_CONF}"
  sudo mkdir -p "${NM_DNSMASQ_DIR}"
  cat <<EOF | sudo tee "${NM_DNSMASQ_CONF}" >/dev/null
# Map the entire zone to localhost (wildcard)
address=/${DOMAIN}/127.0.0.1
address=/${DOMAIN}/::1
EOF

  echo ">>> Restarting NetworkManager"
  sudo systemctl restart NetworkManager

  echo ">>> Resolver status"
  cat /etc/resolv.conf || true
}

configure_via_system_dnsmasq() {
  echo ">>> NetworkManager not active -> configuring system dnsmasq (fallback)"
  install_dnsmasq_if_missing

  echo ">>> Writing system dnsmasq config: ${SYS_DNSMASQ_CONF}"
  sudo mkdir -p /etc/dnsmasq.d
  cat <<EOF | sudo tee "${SYS_DNSMASQ_CONF}" >/dev/null
address=/${DOMAIN}/127.0.0.1
address=/${DOMAIN}/::1
EOF

  echo ">>> Enabling and restarting dnsmasq service"
  sudo systemctl enable dnsmasq --now
  sudo systemctl restart dnsmasq

  # Optional: systemd-resolved integration if it exists, but NEVER fail the script
  if command -v resolvectl >/dev/null 2>&1 && systemctl is-active --quiet systemd-resolved 2>/dev/null; then
    echo ">>> Configuring systemd-resolved routing for ${DOMAIN}"
    sudo resolvectl dns lo 127.0.0.1 || true
    sudo resolvectl domain lo "~${DOMAIN}" || true
  else
    echo ">>> systemd-resolved not active -> skipping resolvectl integration"
    echo ">>> NOTE: Ensure your system resolver uses 127.0.0.1 to query dnsmasq."
  fi
}

# Prefer NetworkManager path if NM is present+active (your case)
if systemctl is-active --quiet NetworkManager 2>/dev/null; then
  configure_via_networkmanager_dnsmasq
else
  configure_via_system_dnsmasq
fi

echo
echo ">>> Testing resolution"
getent hosts "${DOMAIN}" || true
getent hosts "test.${DOMAIN}" || true

echo
echo ">>> Local DNS configured for:"
echo "    ${DOMAIN}"
echo "    *.${DOMAIN}"
