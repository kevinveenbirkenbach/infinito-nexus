#!/usr/bin/env bash
# Enlarge host swap on a GitHub-hosted runner. Consumes all remaining
# space on / minus a reserved buffer for Docker layers, checkout and
# runtime data. Falls back to /mnt when / is too small. Replaces
# whatever swap was already active. Needed on 16 GB runners where
# transient spikes (e.g. peertube plugin install, issue #162) otherwise
# trip the host OOM-killer.
#
# Usage: enlarge_swap.sh [buffer-gb]
# Default buffer: 25 GB (nested Docker images + checkout + runner cache).

set -euo pipefail

BUFFER_GB="${1:-25}"
MIN_SWAP_GB=4   # refuse to create a swapfile smaller than this

sudo swapoff -a || true
sudo rm -f /mnt/swapfile /swapfile

root_free=$(df --output=avail -B1G / | tail -n1 | tr -d ' ')
mnt_free=0
if [ -d /mnt ]; then
	mnt_free=$(df --output=avail -B1G /mnt | tail -n1 | tr -d ' ')
fi

root_swap=$((root_free - BUFFER_GB))
mnt_swap=$((mnt_free - BUFFER_GB))

if [ "$root_swap" -ge "$MIN_SWAP_GB" ]; then
	target=/swapfile
	size=$root_swap
elif [ "$mnt_swap" -ge "$MIN_SWAP_GB" ]; then
	target=/mnt/swapfile
	size=$mnt_swap
else
	echo "Neither / nor /mnt has ${MIN_SWAP_GB}+${BUFFER_GB} GB free for swap" >&2
	df -h / /mnt >&2
	exit 1
fi

sudo fallocate -l "${size}G" "$target"
sudo chmod 600 "$target"
sudo mkswap "$target"
sudo swapon "$target"

echo "Swap of ${size}G created at ${target} (buffer ${BUFFER_GB}G)"
free -h
swapon --show
