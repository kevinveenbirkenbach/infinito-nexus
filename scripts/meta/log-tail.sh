#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${1:-logs}"
LINES="${2:-200}"

echo "=== DEBUG: logs ==="
ls -la "${LOG_DIR}" || true
echo

shopt -s nullglob

found=false
for f in "${LOG_DIR}"/*.log; do
  found=true
  echo "============================================================"
  echo "=== Last ${LINES} lines of: ${f}"
  echo "============================================================"
  tail -n "${LINES}" "${f}" || true
  echo
done

if [[ "${found}" = false ]]; then
  echo "No log files found in ${LOG_DIR}"
fi
