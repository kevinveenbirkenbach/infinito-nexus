# Browsers 🎨

## Description

This Ansible role serves as a wrapper to install and configure multiple browsers on a target system. It integrates the configurations of both Chromium and Firefox, ensuring that each browser is set up with forced installation of key security extensions (uBlock Origin and the KeePassXC browser extension) via Enterprise Policies.

## Overview

The **util-desk-browser** role orchestrates the deployment of two specialized roles: **desk-chromium** and **desk-firefox**. By executing both roles, it provides a unified solution for browser management, making it easier to maintain a secure and consistent browsing environment across your systems.

## Purpose

The purpose of this role is to simplify the automation of browser deployments. Instead of managing separate playbooks or tasks for Chromium and Firefox, this role consolidates browser installation and configuration into one streamlined process.

## Features

- **Unified Browser Management:** Executes both Chromium and Firefox configuration roles.
- **Automated Installation:** Installs Chromium and Firefox along with their essential security extensions.
- **Enforced Security Policies:** Ensures that uBlock Origin and the KeePassXC browser extension are automatically deployed using Enterprise Policies.
- **Seamless Integration:** Easily integrates into your existing automation workflows for a consistent system setup.

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus NonCommercial License](https://s.infinito.nexus/license)
