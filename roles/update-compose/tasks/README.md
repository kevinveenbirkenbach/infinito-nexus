# Update System

## Description

This role serves as a central orchestrator for system updates. It conditionally executes various update roles based on the target system and available directories, ensuring that packages and Docker images are kept up-to-date.

## Overview

This role performs the following tasks:
- Checks if the Docker Compose instances directory exists.
- Executes system updates using platform-specific methods:
  - Uses [pacman](https://wiki.archlinux.org/title/Pacman) for Arch Linux.
  - Uses [apt](https://en.wikipedia.org/wiki/APT_(software)) for Debian-based systems.
- Invokes the Docker update role if Docker Compose instances are found.
- Checks for the presence of the [yay](https://github.com/Jguer/yay) AUR helper and, if installed, triggers an update for AUR packages.

## Purpose

The primary purpose of this role is to streamline system maintenance by delegating updates to the appropriate update roles based on the system’s platform and current configuration.

## Features

- **Conditional Execution:** Runs update roles based on the operating system and available directories.
- **Multi-Platform Support:** Supports both Arch Linux and Debian-based distributions.
- **Docker Image Updates:** Triggers Docker image updates when applicable.
- **AUR Package Updates:** Checks for the AUR helper and updates AUR packages if present.
