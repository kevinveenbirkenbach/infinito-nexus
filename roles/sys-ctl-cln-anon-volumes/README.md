# Cleanup Docker Anonymous Volumes

## Description

This Ansible role installs and executes [`dockreap`](https://github.com/kevinveenbirkenbach/web-app-volume-cleaner), a tool designed to clean up unused anonymous Docker volumes (including symlinks and their targets) to maintain a tidy Docker environment.

## Overview

The role installs the tool via [`pkgmgr`](https://github.com/kevinveenbirkenbach/package-manager) using the `dockreap` alias and runs it with the `--no-confirmation` flag to ensure automatic, non-interactive cleanup.

## Purpose

This role is intended to automate the removal of orphaned Docker volumes that consume unnecessary disk space. It is especially useful in backup, CI/CD, or maintenance routines.

## Features

- **Automated Cleanup:** Runs `dockreap --no-confirmation` to clean up unused anonymous volumes.
- **pkgmgr Integration:** Installs the tool via Kevin’s package manager (`pkgmgr`).
- **Idempotent Execution:** Ensures the tool is installed and run only once per playbook run.
- **Symlink-Aware:** Safely handles symlinked `_data` directories and their targets.