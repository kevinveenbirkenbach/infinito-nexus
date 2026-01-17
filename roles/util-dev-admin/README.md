# Persona: Administrator 🛠️

## Description

This Ansible role installs a collection of essential tools for Linux system administrators on Arch Linux. It provides a base environment for package management, building software, archiving, duplication detection, and more.

Learn more about Linux system administration from the [Arch Wiki](https://wiki.archlinux.org/title/System_administration), [The Linux Documentation Project](https://tldp.org/), and the [GNU Core Utilities](https://www.gnu.org/software/coreutils/).

## Overview

Targeted at Arch Linux, this role sets up utilities commonly used by system administrators, such as `yay` for AUR management, `fdupes` for duplicate detection, `7z` support, `cmake`, and the full `base-devel` toolchain.

## Purpose

This role aims to streamline the configuration of a reliable administrative environment. It's intended for technical users who manage Linux systems regularly and want a reproducible, maintainable toolset.

## Features

- **Installs Core Admin Tools:** Includes `base-devel`, `yay`, `cmake`, `fdupes`, and `p7zip`.
- **Extensible via Dependencies:** Includes additional development tools (`git`, `make`, `gcc`) as dependencies.
- **Persona Integration:** Part of the Infinito.Nexus Persona system for user-centric workstation roles.

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license)
