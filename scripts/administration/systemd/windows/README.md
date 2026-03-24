# 🪟 systemd — Windows / WSL2

This directory contains scripts for managing systemd within a **WSL2** (Windows Subsystem for Linux 2) environment.

---

## 📄 Scripts

### ✅ `enable.sh`

Enables systemd as the WSL2 init system by writing `systemd=true` into `/etc/wsl.conf`.

- Silently exits if not running on WSL2
- Silently exits if systemd is already running (`/run/systemd/system` exists)
- If systemd is configured but not yet active, prints instructions to restart WSL2
- If systemd is not configured at all, appends the `[boot]` section to `/etc/wsl.conf` and triggers `wsl --shutdown` to apply the change

> ⚠️ After this script runs, WSL2 must be fully restarted before systemd-dependent steps (DNS, AppArmor, etc.) will work.

---

## 🔗 Related

- [`../`](../) — systemd administration scripts
- `make wsl2-systemd-check` — Make target that invokes this script
