# Spotify 🎵

## Description

This Ansible role installs the [Spotify](https://www.spotify.com/) desktop client on Arch Linux systems using the [AUR (Arch User Repository)](https://aur.archlinux.org/packages/spotify/).

## Overview

Spotify is a digital music streaming service that gives you access to millions of songs and podcasts. Since it is not available in the official Arch repositories, this role uses an AUR helper (like [`yay`](https://github.com/Jguer/yay)) to install the package.

## Purpose

To automate the installation of Spotify on Arch-based systems while ensuring proper handling of AUR-related tasks through a dedicated helper role.

## Features

- 🎧 Installs the official [Spotify AUR package](https://aur.archlinux.org/packages/spotify)
- 🛠 Uses `yay` (or other helper) via [`kewlfft.aur`](https://github.com/kewlfft/ansible-aur) Ansible module
- 🔗 Declares dependency on `dev-yay` for seamless integration

## Requirements

- The `dev-yay` role must be applied before using this role.
- An AUR helper like `yay` must be available on the system.

## Dependencies

This role depends on:

- [`dev-yay`](../dev-yay) – provides and configures an AUR helper like `yay`

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus NonCommercial License (CNCL)](https://s.infinito.nexus/license)
