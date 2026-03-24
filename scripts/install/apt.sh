#!/usr/bin/env bash
set -euo pipefail

if (($# == 0)); then
	echo "Usage: $0 <package> [package ...]" >&2
	exit 1
fi

sudo apt-get update
sudo apt-get install -y "$@"
