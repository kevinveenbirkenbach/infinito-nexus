# Python Development Utilities 🐍

## Description

This Ansible role sets up a Python development environment on Arch Linux. It includes Python itself, the `pip` package manager, and builds on the general developer persona to support scripting, application development, data science, and more.

Learn more at the [Python Official Site](https://www.python.org/), the [Arch Wiki - Python](https://wiki.archlinux.org/title/Python), and [Wikipedia – Python](https://en.wikipedia.org/wiki/Python_(programming_language)).

## Overview

This role provides the essential tooling for Python developers, enabling immediate use of `python` and `pip` from the command line. It supports both general-purpose scripting and advanced software engineering workflows.

## Purpose

To simplify and standardize the provisioning of Python-ready environments for developers, students, data scientists, and automation engineers.

## Features

- **Installs Python and Pip:** Ensures the interpreter and package manager are available.
- **Persona Integration:** Extends `dev-core` with Python-specific tools.
- **Foundation for Further Stacks:** Ideal starting point for Flask, Django, scientific computing, and automation.

## Customization

Easily extend this role with:
- Python virtualenv tools (`python-virtualenv`, `pyenv`)
- Popular libraries (`numpy`, `requests`, `flask`)
- Framework-specific roles (e.g., `dev-python-django`)

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license)
