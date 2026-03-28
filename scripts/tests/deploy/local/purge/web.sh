#!/usr/bin/env bash
set -euo pipefail

docker exec "${INFINITO_CONTAINER}" bash -lc "
  echo \">>> Cleaning up Nginx configuration files\"
  bash /opt/src/infinito/scripts/container/purge/web.sh || true
"
