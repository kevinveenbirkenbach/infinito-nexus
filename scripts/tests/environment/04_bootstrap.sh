#!/usr/bin/env bash
# Install dependencies and prepare the environment for deployment.
set -euo pipefail

echo "Bootstrapping the development environment: DNS, AppArmor, IPv6, and lint tooling."
make environment-bootstrap

echo "Starting the local compose stack (builds the image if missing)."
make up
