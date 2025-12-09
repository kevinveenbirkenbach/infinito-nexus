# dev-nix

This role installs the Nix package manager in a secure and reproducible way.

## Description

The role provides an offline-friendly and deterministic installation of Nix by
using a locally stored installer script that is verified via SHA256 before
execution. This avoids remote code downloads during Ansible runs and ensures a
stable installation across different systems.

## Overview

The installer script is shipped with the role and copied to the target host.
Its checksum is validated against a predefined SHA256 value. Only if the
checksum matches, the installer is executed in multi-user (daemon) mode.
Optionally, the role can install a small shell snippet to automatically load
the Nix environment.

## Features

- Local, pinned Nix installer (no network download at runtime)
- SHA256 checksum verification
- Multi-user (daemon) installation mode
- Optional shell integration via `/etc/profile.d`
- Fully idempotent and distro-agnostic

## Further Resources

- Nix project: https://nixos.org
- Nix releases: https://releases.nixos.org
- Infinito.Nexus License: https://s.infinito.nexus/license