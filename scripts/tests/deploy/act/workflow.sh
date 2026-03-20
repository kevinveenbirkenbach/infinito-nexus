#!/usr/bin/env bash
set -euo pipefail

# Generic local act runner.
#
# Core variables:
#   ACT_WORKFLOW   workflow file path (for example .github/workflows/test-development.yml)
#   ACT_JOB        optional job id
#   ACT_MATRIX     optional matrix selector (for example dev_runtime_image:debian:bookworm)
#
# Optional execution variables:
#   ACT_EVENT              default: workflow_dispatch
#   ACT_CONTAINER_OPTIONS  default: --privileged
#   ACT_NETWORK            default: host
#   ACT_PULL               default: false
#   ACT_RM                 default: true
#   ACT_FRESH              default: true
#
# Optional cleanup variables (space separated):
#   ACT_CLEANUP_CONTAINERS
#   ACT_CLEANUP_NETWORKS
#   ACT_CLEANUP_COMPOSE_PROJECTS
#   ACT_CLEANUP_SUBNETS       default: 172.30.0.0/24

: "${ACT_EVENT:=workflow_dispatch}"
: "${ACT_WORKFLOW:?ACT_WORKFLOW is not set (e.g. .github/workflows/test-development.yml)}"
: "${ACT_JOB:=}"
: "${ACT_MATRIX:=}"

: "${ACT_CONTAINER_OPTIONS:=--privileged}"
: "${ACT_NETWORK:=host}"
: "${ACT_PULL:=false}"
: "${ACT_RM:=true}"
: "${ACT_FRESH:=true}"

: "${ACT_CLEANUP_CONTAINERS:=}"
: "${ACT_CLEANUP_NETWORKS:=}"
: "${ACT_CLEANUP_SUBNETS:=172.30.0.0/24}"

repo_name="$(basename "$(pwd -P)")"
: "${ACT_CLEANUP_COMPOSE_PROJECTS:=workspace ${repo_name}}"

add_unique() {
	local item="$1"
	shift
	local -n arr_ref="$1"
	local existing
	for existing in "${arr_ref[@]}"; do
		[[ "${existing}" == "${item}" ]] && return 0
	done
	arr_ref+=("${item}")
}

if [[ "${ACT_FRESH}" == "true" ]]; then
	echo ">>> Fresh mode enabled: cleaning stale docker resources"

	declare -a containers=()
	declare -a networks=()

	if [[ -n "${ACT_CLEANUP_CONTAINERS}" ]]; then
		read -r -a tmp_containers <<<"${ACT_CLEANUP_CONTAINERS}"
		for container in "${tmp_containers[@]}"; do
			add_unique "${container}" containers
		done
	fi

	if [[ -n "${ACT_CLEANUP_NETWORKS}" ]]; then
		read -r -a tmp_networks <<<"${ACT_CLEANUP_NETWORKS}"
		for network in "${tmp_networks[@]}"; do
			add_unique "${network}" networks
		done
	fi

	if [[ -n "${ACT_CLEANUP_COMPOSE_PROJECTS}" ]]; then
		read -r -a projects <<<"${ACT_CLEANUP_COMPOSE_PROJECTS}"
		for project in "${projects[@]}"; do
			while IFS= read -r cid; do
				[ -n "${cid}" ] || continue
				add_unique "${cid}" containers
			done < <(docker ps -a --filter "label=com.docker.compose.project=${project}" --format '{{.ID}}')

			while IFS= read -r net; do
				[ -n "${net}" ] || continue
				add_unique "${net}" networks
			done < <(docker network ls --format '{{.Name}}' --filter "label=com.docker.compose.project=${project}")
		done
	fi

	if [[ -n "${ACT_CLEANUP_SUBNETS}" ]]; then
		read -r -a cleanup_subnets <<<"${ACT_CLEANUP_SUBNETS}"
		mapfile -t network_ids < <(docker network ls -q)
		if ((${#network_ids[@]} > 0)); then
			while IFS='|' read -r net_name net_subnet; do
				[ -n "${net_name}" ] || continue
				[[ "${net_name}" =~ _default$ ]] || continue
				for cleanup_subnet in "${cleanup_subnets[@]}"; do
					if [[ "${net_subnet}" == "${cleanup_subnet}" ]]; then
						add_unique "${net_name}" networks
						break
					fi
				done
			done < <(docker network inspect "${network_ids[@]}" --format '{{.Name}}|{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || true)
		fi
	fi

	# Known static names from the development compose stack.
	while IFS= read -r name; do
		[ -n "${name}" ] || continue
		if [[ "${name}" == "infinito-coredns" || "${name}" =~ ^infinito_nexus_ ]]; then
			add_unique "${name}" containers
		fi
	done < <(docker ps -a --format '{{.Names}}')

	add_unique "${repo_name}_default" networks
	add_unique "workspace_default" networks

	if ((${#containers[@]} > 0)); then
		echo ">>> Removing stale containers: ${containers[*]}"
		docker rm -f "${containers[@]}" >/dev/null 2>&1 || true
	fi

	if ((${#networks[@]} > 0)); then
		echo ">>> Removing stale networks: ${networks[*]}"
		docker network rm "${networks[@]}" >/dev/null 2>&1 || true
	fi
fi

echo "=== act: workflow=${ACT_WORKFLOW} event=${ACT_EVENT} job=${ACT_JOB:-<all>} matrix=${ACT_MATRIX:-<none>} ==="

cmd=(act "${ACT_EVENT}" -W "${ACT_WORKFLOW}")
if [[ -n "${ACT_JOB}" ]]; then
	cmd+=(-j "${ACT_JOB}")
fi
if [[ -n "${ACT_MATRIX}" ]]; then
	cmd+=(--matrix "${ACT_MATRIX}")
fi
if [[ -n "${ACT_CONTAINER_OPTIONS}" ]]; then
	cmd+=(--container-options "${ACT_CONTAINER_OPTIONS}")
fi
if [[ -n "${ACT_NETWORK}" ]]; then
	cmd+=(--network "${ACT_NETWORK}")
fi

cmd+=(--pull="${ACT_PULL}")

if [[ "${ACT_RM}" == "true" ]]; then
	cmd+=(--rm)
fi

"${cmd[@]}"
