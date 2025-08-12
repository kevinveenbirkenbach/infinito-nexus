# Shell Development Utilities 🐚

## Description

This Ansible role sets up a minimal yet effective environment for Bash and shell script development on Arch Linux. It includes tools like `shellcheck` that help developers write clean, maintainable, and error-free shell scripts.

Learn more about [ShellCheck](https://www.shellcheck.net/), [Bash](https://www.gnu.org/software/bash/), and general shell scripting via the [Arch Wiki - Bash](https://wiki.archlinux.org/title/Bash).

## Overview

This role expands the general `util-desk-dev-core` by equipping the system with tools specifically aimed at writing and linting shell scripts. It's ideal for DevOps engineers, system administrators, and anyone automating systems with Bash.

## Purpose

The role ensures that the developer can safely and efficiently write shell scripts, catching bugs and stylistic issues early using static analysis.

## Features

- **Installs ShellCheck:** A linting tool for detecting issues in shell scripts.
- **Persona Integration:** Extends the general developer persona for Bash-centric workflows.
- **Lightweight & Fast:** Quick setup with room for future extensions.

## Customization

You can easily extend this role with:
- Additional linting or formatting tools
- Script documentation generators
- Shell environments like `zsh`, `fish`, or `nushell`

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus NonCommercial License (CNCL)](https://s.infinito.nexus/license)