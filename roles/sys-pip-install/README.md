# sys-pip-install

## Description

This role installs or upgrades a Python package **system-wide** using the system `pip` (`python3 -m pip`).
It is intended for CLI tools that should be available globally (e.g., maintenance utilities).

> This role depends on `sys-pip`, which ensures that `pip` is installed on the target system.

## Overview

- Ensures the system `pip` is available (via `sys-pip`).
- Installs or upgrades a package specified by `sys_pip_install_package`.
- Designed for non-interactive automation (CI/maintenance hosts).

## Variables

### Required

- `sys_pip_install_package` (string)  
  Name of the Python package to install (e.g., `dockreap`, `backup-docker-to-local`).

## Notes / Caveats

- The role uses `--break-system-packages` (and `PIP_BREAK_SYSTEM_PACKAGES=1`) to allow installing into the system Python
  on distributions that enforce externally-managed environments.
- Use with care: installing Python packages system-wide can conflict with OS package management.
  For isolated installs of CLI tools, consider `pipx` instead.
