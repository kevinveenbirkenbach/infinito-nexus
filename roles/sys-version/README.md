# System Version 🏷️

## Description

This Ansible role extracts the project version from the local `pyproject.toml` (using `playbook_dir`)
and writes it to `PATH_INFINITO_VERSION` on the managed host.

## Features

- Extracts `version = "..."` from `pyproject.toml` on the control node
- Writes the version file to the target host
- Creates the destination directory if missing

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license)
