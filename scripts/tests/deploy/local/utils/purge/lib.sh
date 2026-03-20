#!/usr/bin/env bash
set -euo pipefail

docker exec -it "${INFINITO_CONTAINER}" bash -lc "
  echo \">>> Cleaning up lib \"
  rm -rv /var/lib/infinito/ || true
"
