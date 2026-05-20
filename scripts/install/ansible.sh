#!/usr/bin/env bash
set -euo pipefail

# 🔁 Reload env after venv.sh: first env-gen runs before the venv exists, so PYTHON is the system fallback.
if [[ -n "${VENV:-}" && -x "${VENV}/bin/python" && "${PYTHON:-}" != "${VENV}/bin/python" ]]; then
	unset INFINITO_ENV_LOADED
	unset PYTHON
	unset PIP
	# shellcheck source=scripts/meta/env/load.sh
	source "${ENV_SH:-scripts/meta/env/load.sh}"
fi

echo "📦 Installing Ansible collections"

: "${PYTHON:?PYTHON not set}"
: "${ANSIBLE_COLLECTIONS_DIR:?ANSIBLE_COLLECTIONS_DIR not set}"

echo "→ Target: ${ANSIBLE_COLLECTIONS_DIR}"
mkdir -p "${ANSIBLE_COLLECTIONS_DIR}"

MAX_ATTEMPTS=5
ATTEMPT=1

GALAXY_REQ="requirements/requirements.galaxy.yml"
GIT_REQ="requirements/requirements.git.yml"

while true; do
	echo "▶️  Attempt ${ATTEMPT}/${MAX_ATTEMPTS}"

	echo "🌐 Trying Galaxy source (${GALAXY_REQ})…"
	if "${PYTHON}" -m ansible.cli.galaxy collection install \
		-r "${GALAXY_REQ}" \
		-p "${ANSIBLE_COLLECTIONS_DIR}" \
		--force-with-deps; then

		echo "✅ Collections installed successfully via Galaxy on attempt ${ATTEMPT}"
		break
	fi

	echo "⚠️  Galaxy install failed on attempt ${ATTEMPT}"

	echo "🔁 Falling back to Git source (${GIT_REQ})…"
	if "${PYTHON}" -m ansible.cli.galaxy collection install \
		-r "${GIT_REQ}" \
		-p "${ANSIBLE_COLLECTIONS_DIR}" \
		--force-with-deps; then

		echo "✅ Collections installed successfully via Git fallback on attempt ${ATTEMPT}"
		break
	fi

	if ((ATTEMPT >= MAX_ATTEMPTS)); then
		echo "❌ Installation failed after ${MAX_ATTEMPTS} attempts."
		echo "   Galaxy and Git fallback both failed."
		exit 1
	fi

	SLEEP_TIME=$((60 + RANDOM % 61))
	echo "⏸️  Attempt ${ATTEMPT} failed for both sources."
	echo "   Waiting ${SLEEP_TIME}s before retry…"

	sleep "${SLEEP_TIME}"
	((ATTEMPT++))
done

echo "🎉 All collections are ready"
