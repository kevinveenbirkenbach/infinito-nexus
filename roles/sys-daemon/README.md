# Core Daemon Reset

## Description

This role resets and cleans up all **Infinito.Nexus** core daemon `systemd` service units that match the configured suffix (`SYS_SERVICE_SUFFIX`).  
It is primarily used in maintenance or reset scenarios when a full service cleanup is required.

## Overview

When the `MODE_RESET` flag is enabled, the role will:

1. **Run Once Per Play:** Guarded by `run_once_sys_daemon` to avoid duplicate execution.
2. **Identify Service Units:** Finds all `/etc/systemd/system/*{{ SYS_SERVICE_SUFFIX }}` units.
3. **Stop and Disable Services:** Gracefully stops and disables matching services.
4. **Remove Unit Files:** Deletes the corresponding unit files from the system.
5. **Reload systemd:** Ensures the service manager state is updated after cleanup.

## Purpose

The main goal of this role is to ensure a clean and consistent state for core daemon services by removing obsolete or stale systemd units.  
This is particularly useful when re-deploying or performing a full environment reset.

## Features

- **Automated Cleanup:** Stops, disables, and removes targeted systemd units.
- **Idempotent Execution:** Runs only once per playbook run.
- **Configurable Targeting:** Matches services using `SYS_SERVICE_SUFFIX`.
- **Systemd Integration:** Reloads daemon state after changes.

## Further Resources

- [systemd Service Management](https://www.freedesktop.org/software/systemd/man/systemctl.html)
- [Infinito.Nexus License](https://s.infinito.nexus/license)

## License

This role is released under the Infinito.Nexus NonCommercial License.
See [license details](https://s.infinito.nexus/license)

## Author Information

Kevin Veen-Birkenbach
Consulting & Coaching Solutions
[https://www.veen.world](https://www.veen.world)