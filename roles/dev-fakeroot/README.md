# Fakeroot

## Description

This Ansible role installs **fakeroot** for the current Linux distribution. Fakeroot enables non-privileged users to simulate root-level file manipulations—ideal for building packages or performing file operations that normally require root permissions.

Learn more about fakeroot on [Wikipedia](https://en.wikipedia.org/wiki/Fakeroot_(software)).

## Purpose

The purpose of this role is to automate the installation of fakeroot so that users can simulate superuser operations without requiring elevated privileges. This is particularly useful in development environments and during package building processes.

## Features

- **Automated Installation:** Installs fakeroot via the OS package manager.
- **Idempotent Execution:** Ensures that fakeroot is installed and remains up to date.
- **Simplified Setup:** Minimizes manual installation steps for environments where fakeroot is required.

## Credits

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

License: [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license)
