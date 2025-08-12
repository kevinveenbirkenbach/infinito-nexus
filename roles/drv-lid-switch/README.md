# Driver Lid Switch 🛑💻

## Description

This Ansible role configures lid switch behavior on Linux systems where the default behavior does not work correctly—particularly on laptops like the HP Spectre x360 14-ef2777ng running Manjaro Linux, Wayland, and GNOME. By default, closing the lid can trigger hibernation or suspend incorrectly, even while docked or on external power.

This role integrates [`setup-hibernate`](https://github.com/kevinveenbirkenbach/setup-hibernate) to configure hibernation support and sets systemd rules to define proper lid switch behavior based on power state.

## Overview

This role addresses a common issue on Linux laptops: closing the lid while docked or plugged in leads to unintended sleep or hibernation. It installs the necessary hibernation tools and updates `/etc/systemd/logind.conf` to:

- Hibernate on lid close when on battery
- Lock the session when on AC power or docked

## Purpose

The purpose of this role is to enforce a consistent and predictable lid switch behavior across power states, improving usability on laptops that otherwise behave unpredictably when the lid is closed.

## Features

- **Installs `setup-hibernate`:** Uses `pkgmgr` to install and initialize hibernation support.
- **Systemd Integration:** Applies proper `logind.conf` settings for lid switch handling.
- **Power-aware Configuration:** Differentiates between battery, AC power, and docked state.
- **Idempotent Design:** Ensures safe re-runs and minimal unnecessary restarts.

## Further Resources
- https://chatgpt.com/share/67ed14d0-4220-800f-a592-82513553fb97
- https://chatgpt.com/share/67ed1520-8a54-800f-98a5-12372413994a
- https://chatgpt.com/share/67ed158b-66d4-800f-b418-e52460c225ce

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus NonCommercial License (CNCL)](https://s.infinito.nexus/license)