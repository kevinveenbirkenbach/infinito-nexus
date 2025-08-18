# Docker Compose Certificate Sync Service

## Description
Keeps Docker Compose services updated with fresh Let’s Encrypt certificates via a systemd oneshot service and timer.

## Overview
Installs a small script and a systemd unit that copy certificates into your Compose project and trigger an Nginx hot-reload (fallback: restart) to minimize downtime.

## Features
- Automatic certificate sync into the Compose project
- Mailu-friendly filenames (`key.pem`, `cert.pem`)
- Nginx hot-reload if available, otherwise restart
- Runs on a schedule you define

## Further Resources
- [Wildcard Certificate Setup (SETUP.md)](./SETUP.md)
- [Role Documentation](https://s.infinito.nexus/code/tree/main/roles/sys-ctl-mtn-cert-deploy)
- [Issue Tracker](https://s.infinito.nexus/issues)
