# Backup Docker to Local

## Description

This Ansible role automates the process of backing up Docker volumes to a local folder. It pulls the [backup-docker-to-local](https://github.com/kevinveenbirkenbach/backup-docker-to-local), installs required software, configures systemd services for both standard and "everything" backup modes, and seeds backup database entries as needed.

## Overview

Optimized for Archlinux, this role ensures that Docker volume backups are performed reliably with minimal manual intervention. It integrates with several dependent roles to verify backup success and manage related tasks, including:
- [sys-svc-directory-validator](../sys-svc-directory-validator/) – Validates backup directories.
- [sys-ctl-cln-faild-bkps](../sys-ctl-cln-faild-bkps/) – Cleans up unsuccessful backup attempts.
- [sys-timer](../sys-timer/) – Schedules recurring backup tasks.
- [sys-bkp-provider](../sys-bkp-provider/) – Manages backup sources.
- [sys-lock](../sys-lock/) – Ensures coordinated maintenance operations.

## Purpose

Backup Docker Volumes to Local is a comprehensive solution that leverages rsync to create incremental backups of Docker volumes, providing seamless recovery for both file and database data. Ideal for ensuring the integrity and security of your container data, this role sets up the necessary environment to safeguard your Docker volumes.

## Features

- **Required Software Installation:** Installs necessary packages (e.g., lsof, python-pandas) via pacman.
- **Git Repository Pull:** Automatically pulls the latest version of the [backup-docker-to-local](https://github.com/kevinveenbirkenbach/backup-docker-to-local).
- **Systemd Service Configuration:** Deploys and reloads two systemd service templates to manage backup tasks.
- **Database Seeding:** Includes tasks to seed and manage a backup database (`databases.csv`) for tracking backup details.
- **Dependency Integration:** Works in conjunction with the dependent roles listed above to verify and manage backups.
