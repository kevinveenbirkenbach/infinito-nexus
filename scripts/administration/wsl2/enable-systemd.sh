#!/usr/bin/env bash
set -euo pipefail

# Only relevant on WSL2
if ! grep -qiE "microsoft|wsl" /proc/version 2>/dev/null; then
	exit 0
fi

# Systemd is already running — nothing to do
if systemctl is-system-running >/dev/null 2>&1; then
	exit 0
fi

echo ">>> WSL2 detected — systemd is not enabled."
echo ">>> Enabling systemd in /etc/wsl.conf..."

if grep -qs "systemd=true" /etc/wsl.conf 2>/dev/null; then
	: # already set, nothing to write
elif grep -qs "^\[boot\]" /etc/wsl.conf 2>/dev/null; then
	sudo sed -i '/^\[boot\]/a systemd=true' /etc/wsl.conf
else
	printf '\n[boot]\nsystemd=true\n' | sudo tee -a /etc/wsl.conf >/dev/null
fi

echo ">>> Restarting WSL2 to apply changes..."
echo ">>> Please reopen this terminal and run: make dev-environment-bootstrap"

/mnt/c/Windows/System32/wsl.exe --shutdown 2>/dev/null || {
	echo ""
	echo ">>> Could not auto-restart WSL2."
	echo ">>> Run this in Windows PowerShell, then re-run make:"
	echo ">>>   wsl --shutdown"
}
