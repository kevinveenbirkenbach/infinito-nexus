# MyBB

## Description

Transform your community engagement with MyBB, a feature-rich forum solution that combines modern design with robust functionality. MyBB fosters dynamic discussions, intuitive moderation, and an energetic user interface that brings people together, creating a vibrant online community.

## Overview

This role deploys MyBB using Docker, leveraging Docker Compose to manage both the MyBB application and its underlying MariaDB database. It also integrates with an Nginx reverse proxy for secure, flexible multi-domain access. Additionally, the role supports the manual installation of MyBB plugins for added extensibility. For detailed installation and configuration instructions, please refer to the [Installation.md](./Installation.md) file.

## Features

- **Multi-Domain Support:** Configure MyBB for multi-domain installations by setting the correct cookie domain and board URL.
- **Plugin Extensibility:** Manually install and activate plugins to extend forum functionality and tailor the user experience.
- **Robust Deployment:** Achieve reliable and scalable deployment of your forum via Docker Compose, ensuring seamless service continuity.
- **Secure and Flexible Access:** Integrate with an Nginx reverse proxy to securely manage traffic and domain access.

## Further Resources

- [MyBB Docker Repository](https://github.com/mybb/docker)
- [MyBB Official Website](https://mybb.com/)

## Credits

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [veen.world](https://www.veen.world).

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
Licensed under [Infinito.Nexus NonCommercial License (CNCL)](https://s.infinito.nexus/license).