#!/usr/bin/env bash
set -euo pipefail

# 🔁 Reload env to pick up newly created venv
if [[ -n "${VENV:-}" && -x "${VENV}/bin/python" && "${PYTHON:-}" != "${VENV}/bin/python" ]]; then
	unset INFINITO_ENV_LOADED
	unset INFINITO_ENV_PYTHON_LOADED
	unset PYTHON
	unset PIP
	# shellcheck source=scripts/meta/env/all.sh
	source "${ENV_SH:-scripts/meta/env/all.sh}"
fi

: "${PYTHON:?PYTHON not set}"

echo "🔗 Installing pre-commit hooks"
"${PYTHON}" -m pre_commit install
