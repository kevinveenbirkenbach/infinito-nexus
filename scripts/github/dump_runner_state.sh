#!/usr/bin/env bash
# Dump disk, memory, swap and docker state of a GitHub-hosted runner.
# Intended as a diagnostic helper that can be called from anywhere
# inside a workflow step (pre/post swap resize, post-deploy failure).
#
# Usage: dump_runner_state.sh [label]
# The label is rendered into the log group title and the step summary.

set -euo pipefail

LABEL="${1:-runner state}"

echo "::group::Runner state — ${LABEL}"

echo "--- date ---"
date -u +'%Y-%m-%dT%H:%M:%SZ'

echo "--- disk (bytes) ---"
df -h / /mnt 2>/dev/null || df -h /

echo "--- disk (inodes) ---"
df -hi / /mnt 2>/dev/null || df -hi /

echo "--- block devices ---"
lsblk -f || true

echo "--- mounts (/, /mnt, /var/lib/docker, /mnt/docker) ---"
mount | grep -E ' / | /mnt | /var/lib/docker | /mnt/docker ' || true

echo "--- docker ---"
docker info 2>/dev/null |
	grep -E 'Docker Root Dir|Storage Driver|Containers|Images' ||
	echo "docker daemon not reachable"

echo "--- memory ---"
free -h

echo "--- swap ---"
swapon --show || echo "no swap active"

echo "--- largest dirs on / (top 15) ---"
sudo du -xh --max-depth=2 / 2>/dev/null | sort -h | tail -15 || true

if [ -d /mnt ]; then
	echo "--- largest dirs on /mnt (top 15) ---"
	sudo du -xh --max-depth=2 /mnt 2>/dev/null | sort -h | tail -15 || true
fi

echo "::endgroup::"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
	root_free=$(df --output=avail -B1G / 2>/dev/null | tail -n1 | tr -d ' ' || echo '?')
	mnt_free=$(df --output=avail -B1G /mnt 2>/dev/null | tail -n1 | tr -d ' ' || echo '?')
	mem_free=$(free -g | awk '/^Mem:/ {print $4"G"}')
	swap_total=$(free -g | awk '/^Swap:/ {print $2"G"}')
	{
		echo "### Runner state — ${LABEL}"
		echo "- / free: **${root_free}G** · /mnt free: **${mnt_free}G**"
		echo "- mem free: **${mem_free}** · swap total: **${swap_total}**"
	} >>"$GITHUB_STEP_SUMMARY"
fi
