# System AUR Helper

## Description

This role ensures that the AUR helper [yay](https://wiki.archlinux.org/title/Yay) is installed on the system. It installs yay via [pacman](https://wiki.archlinux.org/title/Pacman) and creates a dedicated `aur_builder` user to facilitate building AUR packages.

## Overview

The role performs the following tasks:
- Installs the AUR helper [yay](https://wiki.archlinux.org/title/Yay) using pacman.
- Creates an `aur_builder` user with a home directory and adds the user to the wheel group.
- Grants the `aur_builder` user passwordless [sudo](https://en.wikipedia.org/wiki/Sudo) rights for running pacman.

## Purpose

The primary purpose of this role is to streamline AUR package management on Arch Linux systems by ensuring that the required AUR helper is installed and properly configured.

## Features

- **Yay Installation:** Installs the AUR helper [yay](https://wiki.archlinux.org/title/Yay) on Arch Linux.
- **User Creation:** Creates a dedicated `aur_builder` user.
- **Sudo Configuration:** Grants passwordless sudo rights to `aur_builder` for pacman.

## Other Resources
- https://github.com/kewlfft/ansible-aur