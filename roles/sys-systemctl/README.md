# sys-systemctl

Utility role to reset/clean up **systemd** units for a given software stack.  
It can install a unit-file remover tool, delete units that match a configured suffix, and reload the systemd daemon. The role is designed to run **once per play** and is commonly included by other roles (e.g., timer/service roles) to ensure a clean state before (re)deployment.

## Overview

When `MODE_RESET` is enabled, the role will:

1. Install the configured remover tool/package (via `pkgmgr-install`).
2. Remove all unit files that match the configured suffix for the current software.
3. Reload the systemd daemon to apply changes.

A run-once guard (`run_once_sys_systemctl`) prevents repeated execution within the same play run.

## Features

- **Idempotent cleanup** of systemd unit files based on a suffix.
- **Pluggable remover tool** via `UNIT_SUFFIX_REMOVER_PACKAGE`.
- **Daemon reload** to immediately apply changes.
- **Run-once safety** across the play to avoid redundant work.

## Variables

| Variable                     | Type    | Default     | Description                                                                                 |
|-----------------------------|---------|-------------|---------------------------------------------------------------------------------------------|
| `MODE_RESET`                | bool    | `false`     | If `true`, executes the reset/cleanup tasks.                                                |
| `SYS_SERVICE_SUFFIX`        | string  | *required*  | Suffix used to identify unit files belonging to the software stack (e.g., `.infinito.nexus`). |
| `SOFTWARE_NAME`             | string  | *required*  | Logical software identifier passed to the remover tool.                                      |
| `UNIT_SUFFIX_REMOVER_PACKAGE` | string| `"unsure"`  | Package/command used to remove the unit files. Must provide a CLI compatible with `-s`.     |

> **Note:** The role expects the remover tool to support a command pattern like:
> ```
> <UNIT_SUFFIX_REMOVER_PACKAGE> -s '<SOFTWARE_NAME>'
> ```
> Replace `UNIT_SUFFIX_REMOVER_PACKAGE` with your actual utility (or wrapper script) that removes all matching unit files.

## Tasks Flow

- `tasks/main.yml`
  - Includes `tasks/01_reset.yml` **only when** `MODE_RESET` is `true`.
  - Loads `utils/run_once.yml` once to set `run_once_sys_systemctl`.

- `tasks/01_reset.yml`
  - Installs `UNIT_SUFFIX_REMOVER_PACKAGE` via `pkgmgr-install`.
  - Executes the remover command to purge unit files for `SOFTWARE_NAME` / `SYS_SERVICE_SUFFIX`.
  - Runs `systemctl daemon-reload`.

## Dependencies

- `pkgmgr-install` (role): used to install `UNIT_SUFFIX_REMOVER_PACKAGE`.

