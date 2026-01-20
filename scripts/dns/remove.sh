#!/usr/bin/env bash
set -euo pipefail

DOMAIN="infinito.example"

NM_CONF="/etc/NetworkManager/conf.d/00-infinito-dnsmasq.conf"
NM_DNSMASQ_CONF="/etc/NetworkManager/dnsmasq.d/${DOMAIN}.conf"

SYS_DNSMASQ_CONF="/etc/dnsmasq.d/${DOMAIN}.conf"

echo ">>> Removing local DNS for *.${DOMAIN}"

# Remove NetworkManager dnsmasq setup
if systemctl is-active --quiet NetworkManager 2>/dev/null; then
  echo ">>> NetworkManager active -> removing NM dnsmasq config"
  sudo rm -f "${NM_CONF}" "${NM_DNSMASQ_CONF}"
  sudo systemctl restart NetworkManager
fi

# Remove system dnsmasq snippet (fallback setup)
sudo rm -f "${SYS_DNSMASQ_CONF}" || true

# If system dnsmasq is active, restart to apply
if systemctl is-active --quiet dnsmasq 2>/dev/null; then
  sudo systemctl restart dnsmasq || true
fi

echo ">>> Removed."
