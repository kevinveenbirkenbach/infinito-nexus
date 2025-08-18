# Certbot Reaper

## Description

This Ansible role automates the detection, revocation and deletion of unused Let's Encrypt certificates. It leverages the [`certreap`](https://github.com/kevinveenbirkenbach/certreap) tool to identify certificates no longer referenced by any active NGINX configuration and removes them automatically.

## Overview

- Installs the `certreap` cleanup tool using the `pkgmgr-install` role
- Deploys and configures a systemd unit
- (Optionally) Sets up a recurring cleanup via a systemd timer using the `sys-timer` role
- Integrates with `sys-ctl-alm-compose` to send failure notifications
- Ensures idempotent execution with a `run_once_sys_ctl_cln_certs` flag

## Features

- **Certificate Cleanup Tool Installation**  
  Uses `pkgmgr-install` to install the `certreap` binary.

- **Systemd Service Configuration**  
  Deploys service and reloads/restarts it on changes.

- **Systemd Timer Scheduling**  
  Optionally wires in a timer via the `sys-timer` role, controlled by the `on_calendar_cleanup_certs` variable.

- **Smart Execution Logic**  
  Prevents multiple runs in one play by setting a `run_once_sys_ctl_cln_certs` fact.

- **Failure Notification**  
  Triggers service on failure.

## Further Resources

- [certreap on GitHub](https://github.com/kevinveenbirkenbach/certreap)  
- [Ansible community.general.pacman module](https://docs.ansible.com/ansible/latest/collections/community/general/pacman_module.html)  
- [Infinito.Nexus NonCommercial License](https://s.infinito.nexus/license)  
- [systemd.unit(5) manual](https://www.freedesktop.org/software/systemd/man/systemd.unit.html)  
