# msmtp 📧

## Description

This Ansible role installs and configures **msmtp** and **msmtp-mta** on Arch Linux systems. It provides a lightweight SMTP client that serves as a drop-in replacement for the traditional sendmail command, enabling reliable email delivery via an external SMTP server. For more background on SMTP, see [SMTP on Wikipedia](https://en.wikipedia.org/wiki/SMTP).

## Overview

Tailored for Arch Linux, this role uses the `pacman` package manager to install **msmtp** and **msmtp-mta**. It then deploys a pre-configured msmtprc file via a Jinja2 template that defines settings for authentication, TLS, and the target SMTP server. This role is ideal for environments where automated email notifications or direct email sending are required.

## Purpose

The purpose of this role is to automate the setup of a lightweight SMTP client that acts as a sendmail replacement. By configuring msmtp, the role facilitates direct email sending using your SMTP server credentials, making it a simple yet effective solution for system notifications and other email-based communications.

## Features

- **Installs msmtp and msmtp-mta:** Uses `pacman` to install the required packages.
- **Customizable SMTP Configuration:** Deploys a customizable msmtprc configuration file with parameters for TLS, authentication, and server details.
- **Drop-in sendmail Replacement:** Configures msmtp to serve as the default sendmail command.
- **Idempotent Setup:** Ensures the tasks run only once with internal flagging.
- **Integration Ready:** Easily integrates with other system roles within the Infinito.Nexus environment for automated notifications.

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus NonCommercial License](https://s.infinito.nexus/license)