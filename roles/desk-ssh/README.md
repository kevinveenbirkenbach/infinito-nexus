# SSH Agent 🔐

## Description

This Ansible role ensures a functional and persistent SSH Agent setup on Arch Linux (Manjaro) systems running GNOME with Wayland. It manages SSH configuration by cloning a remote Git repository into the user's `~/.ssh` directory and sets up a systemd user service to start the SSH agent automatically at login.

To understand the broader context of SSH, read more on [Wikipedia – SSH](https://en.wikipedia.org/wiki/Secure_Shell) or visit the official [OpenSSH project](https://www.openssh.com/).

This role was designed and validated in the context of [this discussion](https://chatgpt.com/share/67ed0e25-7240-800f-9ab2-9fffc569bc20) on configuring SSH agents for KeePassXC compatibility under Wayland sessions.

## Overview

This role is intended for Manjaro/Arch systems where `gnome-keyring` no longer reliably manages `ssh-agent` due to changes in behavior under Wayland. It works by deploying a `systemd --user` service, making SSH Agent integration predictable and independent of graphical environment quirks.

## Purpose

The purpose of this role is to automate the provisioning of SSH agent capabilities and synchronize the `.ssh` directory from a Git repository. This enables users to access private repositories or authenticate with remote servers immediately after login.

## Features

- **Clones a remote SSH config repository** into `~/.ssh` using the `desk-git` role.
- **Deploys and enables a systemd user service** for `ssh-agent`.
- **Ensures environment compatibility** by injecting the `SSH_AUTH_SOCK` variable into either `.bash_profile` or `.profile`.
- **Fails gracefully** with an optional debug message if the Git repository is unreachable.
- **KeePassXC ready**: Ensures compatibility with password managers that support SSH agent integration.

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus NonCommercial License](https://s.infinito.nexus/license)
