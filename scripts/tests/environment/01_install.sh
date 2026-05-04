#!/usr/bin/env bash
# Install package prerequisites and repository dependencies.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/tests/environment/utils/common.sh
source "${SCRIPT_DIR}/utils/common.sh"

bash "${REPO_ROOT}/scripts/install/package.sh"

echo "Installing Python tooling, Ansible collections, and all repository dependencies."
make install
