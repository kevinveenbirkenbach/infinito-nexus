# Installation Guide

Use this guide to install the `infinito` CLI with the method that fits your workflow.

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
make environment-bootstrap
```

This prepares the repository for local development.

`make environment-bootstrap` also installs the repository's local `pre-commit` hooks for this checkout.

If you additionally want a local override marker for Compose env-file layering, run the optional manual step below:

```bash
make mark-development
```

All available `make` commands are documented in the [Makefile Commands](../contributing/tools/makefile.md) reference.
For a worked example of how these commands interact — including build, bootstrap, test, deploy, and teardown — see the [environment test suite](../../scripts/tests/environment/README.md).
For further information on setting up a local development environment, see [CONTRIBUTING.md](../../CONTRIBUTING.md).

For inventory creation and deployment, continue with the [Administration Guide](administration.md).
