#!/usr/bin/env bash
set -euo pipefail

docker exec -it "${INFINITO_CONTAINER}" bash -lc "
  echo \">>> Cleaning up NGinxx configuration files\"
  bash /opt/src/infinito/scripts/administration/purge_web.sh || true
"
