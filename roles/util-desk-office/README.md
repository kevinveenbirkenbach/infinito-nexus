# Office Tools

## Description

This Ansible role installs a comprehensive suite of office productivity tools on Pacman-based Linux distributions, including a web browser, email client, e-book manager, and document editor.

## Overview

The `util-desk-office` role uses the `community.general.pacman` module to:

1. Install **Chromium** (web browser)  
2. Install **Thunderbird** (email and RSS client)  
3. Install **Calibre** (e-book management software)  
4. Install **ReText** (Markdown and reStructuredText editor)  

## Features

* Idempotent installation of all specified office packages  
* Supports any Pacman-based distribution (e.g., Arch Linux)  
* Easily extendable by adding or removing package names  

## Further Resources
* [Infinito.Nexus GitHub repository](https://s.infinito.nexus/code)
