# Update pkgmgr

## Description

This role checks if the [package manager](https://github.com/kevinveenbirkenbach/package-manager) is available on the system. If so, it runs `pkgmgr update --all` to update all repositories managed by the `pkgmgr`.

## Overview

This role performs the following tasks:
- Checks if the `pkgmgr` command is available.
- If available, runs `pkgmgr update --all` to update all repositories.

## Purpose

The purpose of this role is to simplify system updates by using the `pkgmgr` package manager to handle all repository updates with a single command.

## Features

- **Conditional Execution**: Runs only if the `pkgmgr` command is found on the system.
- **Automated Updates**: Automatically runs `pkgmgr update --all` to update all repositories.

## License

Infinito.Nexus NonCommercial License (CNCL)  
[Learn More](https://s.infinito.nexus/license)


