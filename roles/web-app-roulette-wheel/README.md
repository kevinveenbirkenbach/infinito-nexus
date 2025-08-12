# Roulette Wheel

## Warning
This role isn't actively maintained. Use it with caution in production environments.

## Overview
This role deploys and configures the Roulette Wheel application using Docker Compose. It pulls the latest source code from a Git repository, builds a Docker image from a Node.js base, and starts the application on a user-defined local HTTP port.

## Description
Roulette Wheel is a Node.js-based front-end application that is containerized using Docker. The role accomplishes the following:
- **Repository Integration:** Automatically clones or updates the application repository from GitHub.
- **Dockerfile Management:** Uses a custom Dockerfile (built on a Node.js image) to install dependencies, build the application, and define the startup command.
- **Container Deployment:** Integrates with Docker Compose for container orchestration, making it easy to manage the application's lifecycle.

## Features
- **Dockerized Deployment:** Packages the application in a Docker container for consistent and isolated runtime.
- **Automated Builds:** Uses an automated Docker build process with a dedicated Dockerfile.
- **Configurable Ports:** Exposes the application through a customizable host port.
- **Git Integration:** Ensures that the application source code is up-to-date by pulling from the specified Git repository.

## Other Resources
- [Roulette Wheel on GitHub](https://github.com/p-wojt/roulette-wheel)
- [Packaging Front-End Projects into Docker Images (Dev.to)](https://dev.to/ms314006/how-to-package-front-end-projects-into-web-app-images-and-use-it-with-webpack-go3)
- [Stack Overflow: Dockerfile to Run NodeJS Static Content](https://stackoverflow.com/questions/53178820/dockerfile-to-run-nodejs-static-content-in-docker-container)
- [Stack Overflow: Invalid Host Header Message with Webpack Dev Server](https://stackoverflow.com/questions/43619644/i-am-getting-an-invalid-host-header-message-when-connecting-to-webpack-dev-ser)

## Credits
Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [veen.world](https://www.veen.world).  
Licensed under the [Infinito.Nexus NonCommercial License (CNCL)](https://s.infinito.nexus/license).
