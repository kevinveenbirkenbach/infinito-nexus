# 🌍 Global CSS Injection for NGINX

## Description

This Ansible role ensures **consistent global theming** across all NGINX-served applications by injecting CSS files.  
The role leverages [`colorscheme-generator`](https://github.com/kevinveenbirkenbach/colorscheme-generator/) to generate a dynamic, customizable color palette for light and dark mode, compatible with popular web tools like **Bootstrap**, **Keycloak**, **Nextcloud**, **Taiga**, **Mastodon**, and many more.

## Overview

This role deploys a centralized global stylesheet that overrides the default theming of web applications served via NGINX. It's optimized to run only once per deployment and generates a **cache-busting version number** based on file modification timestamps.  
It includes support for **dark mode**, **custom fonts**, and **extensive Bootstrap and UI component overrides**.

## Purpose

The goal of this role is to provide a **single source of truth for theming** across your infrastructure.  
It makes all applications feel like part of the same ecosystem — visually and functionally.

## Features

- 🎨 **Dynamic Theming** via [`colorscheme-generator`](https://github.com/kevinveenbirkenbach/colorscheme-generator/)
- 📁 **Unified CSS Base Configuration** deployment for all NGINX applications
- 🌒 **Dark mode support** out of the box
- 🚫 **No duplication** – tasks run once per deployment
- ⏱️ **Versioning logic** to bust browser cache
- 🎯 **Bootstrap override compatibility**
- 🧩 **Theme support for Keycloak, Nextcloud, Gitea, LAM, Peertube, and more**

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license)
