# BigBlueButton

## Description

This Ansible role deploys [BigBlueButton](https://bigbluebutton.org/) using Docker Compose. It includes support for Greenlight, OIDC, LDAP, TURN/STUN, health checks, and a modular `.env` setup. This role is ideal for educational institutions and teams requiring a self-hosted video conferencing solution.

> 🔧 **Note**: The database layer should be decoupled in a future release to improve modularity and integration.

## Overview

This role provides a fully automated deployment of [BigBlueButton](https://bigbluebutton.org/) using Docker Compose on Arch Linux. It manages the entire lifecycle of the deployment, from cloning the upstream Docker repository and generating the `.env` configuration to customizing `docker-compose.yml` for volume usage, WebSocket proxying, and optional LDAP/OIDC integration.

The setup includes conditional Greenlight activation, WebRTC support via TURN/STUN, and various fixes for known container orchestration issues. The role is modular and integrates seamlessly with the Infinito.Nexus infrastructure, including reverse proxy configuration, domain management, and secrets templating.

By default, BigBlueButton is deployed with best-practice hardening, modular secrets, and support for multiple authentication methods and scalable storage backends.

## Features

- 🐳 **Docker-based** deployment via official [bigbluebutton/docker](https://github.com/bigbluebutton/docker)
- ✅ **Greenlight** (v3) frontend support
- 🔐 **SSO with OIDC & LDAP** (optional)
- 🧱 Automatic `.env` templating and domain/Nginx integration
- 🛠 Volume patching and Docker Compose customization
- 📬 SMTP integration and Greenlight admin creation
- 🧪 Workarounds for known Docker Compose or Etherpad issues

## Single Sign-On (SSO)

- Docs: [External Authentication](https://docs.bigbluebutton.org/greenlight/v3/external-authentication/)
- Supports:
  - ✅ OpenID Connect (OIDC)
  - ✅ LDAP (with custom DN and filters)
  - 🧩 Custom OAuth2 flows via ENV vars

## System Requirements

- Arch Linux with Docker, Compose, and Nginx roles pre-installed
- DNS and reverse proxy configuration using `srv-proxy-core`
- Functional email system for Greenlight SMTP

## Important Resources

- [BigBlueButton Docker Docs](https://docs.bigbluebutton.org/greenlight/gl-install.html#setting-bigbluebutton-credentials)
- [Networking Fixes & Issues](https://stackoverflow.com/questions/53347951/web-app-network-not-found)
- [Traefik + Docker Tutorial](https://goneuland.de/big-blue-button-mit-web-app-und-traefik-installieren/)
- [Etherpad Healthcheck Bug](https://chatgpt.com/c/67a0fc7e-5104-800f-bb6b-3731e2f83b7b)
- [Virtual Interfaces Cleanup](https://www.cyberciti.biz/faq/linux-command-to-remove-virtual-interfaces-or-network-aliases/)