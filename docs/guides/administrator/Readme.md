# Administrator Guide

This guide is for **system administrators** who are deploying and managing Infinito.Nexus infrastructure.

## Setting Up Infinito.Nexus 🏗️
Follow these guides to install and configure Infinito.Nexus:
- [Setup Guide](SETUP_GUIDE.md)
- [Configuration Guide](CONFIGURATION.md)
- [Deployment Guide](DEPLOY.md)

## Key Responsibilities 🔧
- **User Management** - Configure LDAP, Keycloak, and user permissions.
- **Security & Backups** - Set up `sys-bkp-rmt-2-loc`, `svc-bkp-loc-2-usb`, and `core-security` roles.
- **Application Hosting** - Deploy services like `Nextcloud`, `Matrix`, `Gitea`, and more.
- **Networking & VPN** - Configure `WireGuard`, `OpenVPN`, and `Nginx Reverse Proxy`.

## Managing & Updating Infinito.Nexus 🔄
- Regularly update services using `update-docker`, `update-pacman`, or `update-apt`.
- Monitor system health with `sys-ctl-hlth-btrfs`, `sys-ctl-hlth-webserver`, and `sys-ctl-hlth-docker-container`.
- Automate system maintenance with `sys-lock`, `sys-ctl-cln-bkps`, and `sys-ctl-rpr-docker-hard`.

For more details, refer to the specific guides above.