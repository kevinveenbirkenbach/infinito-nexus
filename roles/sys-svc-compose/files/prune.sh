#!/bin/bash

set -euo pipefail

echo "Docker disk usage before cleanup:"
container system df || true

container container prune -f || true
container image prune -af || true
container volume prune -f || true

container buildx prune -af || true
container builder prune -af || true

echo "Docker disk usage after cleanup:"
container system df || true
