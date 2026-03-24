#!/usr/bin/env bash
set -euo pipefail

docker exec "${INFINITO_CONTAINER}" bash -lc "
  echo \">>> Deleting inventory \"
  rm -rv ${INVENTORY_DIR} || true
"
