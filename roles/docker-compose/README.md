# Docker Compose

## Description

This Ansible role manages Docker Compose project structures and workflows for applications on Arch Linux. It creates dedicated instance directories, manages `.env` and `docker-compose.yml` files, and provides automation logic for project reset, rebuild, and startup sequences.

Refer to the [Docker Compose documentation](https://docs.docker.com/compose/), the [Arch Wiki – Docker](https://wiki.archlinux.org/title/Docker), and [Compose CLI reference](https://docs.docker.com/compose/cli-command/) for more details.

## Overview

This role creates a flexible directory layout for managing Docker Compose projects across environments. It ensures directories are initialized, optionally reset, and kept clean using internal flags like `MODE_RESET` or `MODE_CLEANUP`.

## Purpose

To offer a centralized, extensible system for managing containerized applications using Docker Compose within the Infinito.Nexus architecture. The role allows easy integration of services, secrets, configurations, and custom behaviors per application.

## Features

- **Dynamic Directory Structure:** Creates per-application instance folders for Compose setups.
- **Reset Logic:** Cleans previous Compose project files and data when `MODE_RESET` is enabled.
- **Handlers for Runtime Control:** Automatically builds, sets up, or restarts containers based on handlers.
- **Template-ready Service Files:** Predefined service base and health check templates.
- **Integration Support:** Compatible with `srv-proxy-core` and other Infinito.Nexus service roles.

## Administration Tips

For administration tips checkout [this](Administration.md).

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus NonCommercial License](https://s.infinito.nexus/license)