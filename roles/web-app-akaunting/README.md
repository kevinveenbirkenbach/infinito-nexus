# Akaunting

## Description

This Ansible role sets up and manages Akaunting, an innovative online accounting software, using Docker and Docker Compose. Empower your financial management with Akaunting—a dynamic and feature-rich accounting platform designed to simplify your bookkeeping and boost your business growth. Enjoy intuitive tools, real-time insights, and an energetic approach to your finances.

For detailed administration and troubleshooting, check the [Administration Reference](./Administration.md) and the [Installation Guide](./Installation.md).

## Overview

This role provides a comprehensive Dockerized environment for running Akaunting. It deploys the Akaunting application alongside a MariaDB database, configures environment variables, and integrates with Nginx as a reverse proxy. This setup is ideal for both production and development environments.

### Key Features

- **Complete Dockerized Deployment**: Uses Docker Compose to run Akaunting and its associated database.
- **Environment Configuration**: Automatically creates and configures the necessary environment files.
- **Nginx Integration**: Sets up Nginx for handling domain-specific requests and SSL termination.
- **Manual Update and Log Access**: Provides guidance for viewing logs, accessing containers, and performing manual updates.

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license)