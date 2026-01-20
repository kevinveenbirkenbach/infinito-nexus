#!/usr/bin/env bash
set -euo pipefail

DOCKER_DATA_ROOT="/mnt/docker"
DOCKER_TMP="/mnt/docker-tmp"
MIGRATED_MARKER="${DOCKER_DATA_ROOT}/.migrated"
DAEMON_JSON="/etc/docker/daemon.json"

log()  { echo ">>> $*"; }
warn() { echo "!!! WARNING: $*" >&2; }

if [[ "$(id -u)" -ne 0 ]]; then
  SUDO="sudo"
else
  SUDO=""
fi

log "Preparing directories"
$SUDO mkdir -p "${DOCKER_DATA_ROOT}" "${DOCKER_TMP}"
$SUDO chmod 1777 "${DOCKER_TMP}"

log "Stopping docker"
$SUDO systemctl stop docker || true

log "Writing ${DAEMON_JSON} (data-root=${DOCKER_DATA_ROOT})"
$SUDO mkdir -p "$(dirname "${DAEMON_JSON}")"

# Keep it minimal on purpose; overwrite is predictable in CI.
# If you later need to preserve other daemon settings, we can switch to a JSON-merge approach.
$SUDO tee "${DAEMON_JSON}" >/dev/null <<EOF
{
  "data-root": "${DOCKER_DATA_ROOT}"
}
EOF

log "Starting docker"
$SUDO systemctl start docker

log "Waiting for docker daemon to become ready"
for ((n=0; n<30; n++)); do
  if docker info >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

root="$(docker info -f '{{.DockerRootDir}}' 2>/dev/null || true)"
[[ "$root" == "${DOCKER_DATA_ROOT}" ]] || { echo "ERROR: DockerRootDir=$root"; exit 1; }

log "Verifying"
docker info -f 'Docker Root Dir: {{.DockerRootDir}}' || true
df -h || true

# Ensure DOCKER_TMPDIR is set for the current process *and* future workflow steps
export DOCKER_TMPDIR="${DOCKER_TMP}"

if [[ -n "${GITHUB_ENV:-}" && -f "${GITHUB_ENV}" ]]; then
  log "Persisting DOCKER_TMPDIR=${DOCKER_TMP} via GITHUB_ENV"
  echo "DOCKER_TMPDIR=${DOCKER_TMP}" >> "${GITHUB_ENV}"
else
  log "GITHUB_ENV not set -> DOCKER_TMPDIR exported for current shell only"
fi

log "Done"
