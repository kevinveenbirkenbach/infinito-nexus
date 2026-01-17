# Backup to USB

## Description

This Ansible role automates backups to a removable USB device on Arch Linux systems. It ensures that a custom Python backup script is deployed, the necessary systemd units are configured, and backups are triggered whenever the specified USB mount point becomes available.

## Overview

Designed for Arch Linux, this role validates configuration variables (`mount`, `target`, `source`), installs the backup script, generates a systemd service, and sets up a corresponding mount unit. When the USB device is mounted, the service runs the script to synchronize files from the source directory to the USB target, preserving previous snapshots via hard links.

## Purpose

The purpose of this role is to provide a reliable, idempotent solution for local backups to a swappable USB drive. By automating the entire workflow—from variable checks and script deployment to service orchestration and snapshot management—it reduces manual intervention and integrates seamlessly with other Infinito.Nexus roles for comprehensive system automation.

## Features

* **Configuration Validation:** Fails early if any of `backup_to_usb_mount`, `backup_to_usb_target`, or `backup_to_usb_source` is empty.
* **Script Deployment:** Copies the `svc-bkp-loc-2-usb.py` backup script to the target path with correct ownership and permissions.
* **Systemd Integration:** Generates and installs a systemd mount unit for the USB device and a oneshot service that triggers backup upon mount.
* **Snapshot Backups:** Uses `rsync --link-dest` to create incremental snapshots and preserve previous versions without duplicating unchanged files.
* **Idempotent Runs:** Ensures tasks only run when needed and leverages Ansible’s `assert` and state management for consistent behavior.
* **Service Reload Handlers:** Automatically reloads the systemd service when template changes occur.

## Credits

Developed and maintained by **Kevin Veen-Birkenbach**.
Visit [veen.world](https://www.veen.world) for more information.

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)
License: [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license)
