# ⚙️ systemd Administration Scripts

This directory contains scripts for managing systemd across different platforms and environments used in Infinito Nexus development.

---

## 📁 Subdirectories

### ✅ [`enable/`](enable/)

Platform-specific scripts for enabling systemd where it is not active by default.

- **`windows.sh`** — enables systemd as the WSL2 init system via `/etc/wsl.conf` and restarts WSL2 if needed

---

## 🔗 Related

- `make wsl2-systemd-check` — top-level Make target for WSL2 systemd setup
