# Base Development Toolchain

## Description

Base development toolchains provide the core build tools (compilers, linkers, make, etc.) required to compile software from source. Common examples include `base-devel` on Arch Linux, `build-essential` on Debian/Ubuntu, and `@development-tools` on Fedora/CentOS.

## Overview

This role installs distro-specific equivalents of core build tooling so systems are ready for compiling software from source. After deploying this role, all common build dependencies are available on the system.

## Features

- Installs distro-specific base development packages:
  - Archlinux: `base-devel`
  - Debian/Ubuntu: `build-essential`
  - Fedora/CentOS: `@development-tools`
- Ensures your system is ready for software compilation and development

## Further Resources

- [Arch Wiki: base-devel](https://wiki.archlinux.org/title/Arch_Linux_package_guidelines)
- [Debian package: build-essential](https://packages.debian.org/stable/build-essential)
- [DNF groups: development-tools](https://dnf.readthedocs.io/en/latest/command_ref.html#group-command)

## Credits

Developed and maintained by **Kevin Veen-Birkenbach**.
Learn more at [veen.world](https://www.veen.world).
Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code).
Licensed under the [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license).
