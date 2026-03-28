# Installation Guide

Use this guide to install the `infinito` CLI with the method that fits your workflow.

## Install via Package Manager

Install the CLI via [Kevin's Package Manager](https://github.com/kevinveenbirkenbach/package-manager) and inspect the available commands:

```sh
pkgmgr install infinito
infinito --help
```

## Run with Docker

Build the image and run the CLI. For more options, see the [Docker Guide](../Docker.md).

```bash
docker build -t infinito:latest .
docker run --rm -it infinito:latest infinito --help
```

## Develop from Source

Clone the repository and install the project from the repository root:

```bash
git clone https://github.com/infinito-nexus/core.git
cd core
make install
```

This prepares the repository for local development.

For inventory creation and deployment, continue with the [Administration Guide](administration.md).
