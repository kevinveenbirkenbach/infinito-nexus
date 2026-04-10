# Roulette Wheel

## Description

[Roulette Wheel](https://github.com/p-wojt/roulette-wheel) is a Node.js-based front-end application that simulates a roulette wheel in the browser.

## Overview

This role deploys and configures the Roulette Wheel application using Docker Compose. It pulls the latest source code from a Git repository, builds a Docker image from a configurable Node.js base, and starts the application on a user-defined local HTTP port.

## Features

- **Dockerized Deployment:** Packages the application in a Docker container for consistent and isolated runtime.
- **Automated Builds:** Uses an automated Docker build process with a dedicated `Dockerfile`.
- **Configurable Ports:** Exposes the application through a customizable host port.
- **Git Integration:** Ensures that the application source code is up-to-date by pulling from the specified Git repository.

## Further Resources

- [Roulette Wheel on GitHub](https://github.com/p-wojt/roulette-wheel)
- [Stack Overflow: Invalid Host Header with Webpack Dev Server](https://stackoverflow.com/questions/43619644/i-am-getting-an-invalid-host-header-message-when-connecting-to-webpack-dev-ser)

## Credits

Developed and maintained by **Kevin Veen-Birkenbach**.
Learn more at [veen.world](https://www.veen.world).
Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code).
Licensed under the [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license).
