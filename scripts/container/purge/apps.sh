#!/usr/bin/env bash
# App-keyed purge orchestrator. Maps each app id in $APPS to its compose
# entity, then for each entity runs the entity-keyed primitives
# (db, compose, dir) and finally wipes the matching token-store entries
# via utils.data.tokens. Tokens live outside /opt/compose and would
# otherwise survive entity purges, breaking matrix-deploy variant
# transitions (stale token slips past the empty-token guard in
# sys-front-inj-matomo and the next round 502s on the public matomo URL).
#
# Expects:
#   APPS  (required) e.g. "web-app-nextcloud" or "web-app-keycloak,web-app-matomo"
#
# Designed to be invoked from the host via:
#   docker exec -e APPS="${APPS}" <container> \
#     bash /opt/src/infinito/scripts/container/purge/apps.sh  # nocheck: self-path-reference

set -euo pipefail
cd /opt/src/infinito

: "${APPS:?APPS is not set (e.g. APPS=web-app-nextcloud)}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENTITY_DIR="${SCRIPT_DIR}/entity"

apps_raw="${APPS//,/ }"
read -r -a apps <<<"${apps_raw}"

if [[ "${#apps[@]}" -lt 1 ]]; then
	echo "!!! WARNING: APPS is empty after parsing: skipping purge"
	exit 0
fi

if [[ -f "scripts/meta/env/python.sh" ]]; then
	# shellcheck source=scripts/meta/env/python.sh
	source "scripts/meta/env/python.sh"
fi
python_bin="${PYTHON:-python3}"

declare -A seen_entities=()
entities=()

for app in "${apps[@]}"; do
	[[ -n "${app}" ]] || continue

	entity="$("${python_bin}" -c 'from utils.roles.entity_name import get_entity_name; import sys; print(get_entity_name(sys.argv[1]) or "")' "${app}")"

	if [[ -z "${entity}" ]]; then
		echo "!!! WARNING: could not derive entity from APPS=${app}: skipping"
		continue
	fi

	if [[ ! -d "/opt/compose/${entity}" ]]; then
		echo "!!! WARNING: /opt/compose/${entity} not found for APPS=${app}: skipping"
		continue
	fi

	if [[ -z "${seen_entities[${entity}]:-}" ]]; then
		seen_entities[${entity}]=1
		entities+=("${entity}")
		echo ">>> Derived entity from APPS=${app}: ${entity}"
	fi
done

echo ">>> Wiping token-store entries for: ${apps[*]}"
"${python_bin}" -m utils.cleanup.tokens "${apps[@]}" || true

if [[ "${#entities[@]}" -lt 1 ]]; then
	echo "!!! WARNING: no valid entities found: skipping entity purge"
	exit 0
fi

for entity in "${entities[@]}"; do
	echo
	echo ">>> Purging entity: ${entity}"
	bash "${ENTITY_DIR}/db.sh" "${entity}" || true
	bash "${ENTITY_DIR}/compose.sh" "${entity}" || true
	bash "${ENTITY_DIR}/dir.sh" "${entity}" || true
done
