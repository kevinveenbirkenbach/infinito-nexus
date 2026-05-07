#!/usr/bin/env bash
# Aggressively prune Nix data: GC + optimise. CI/Debug cleanup to prevent
# huge disk usage from Nix store + old generations.
#
# Args:
#   $1 nix_bin -- absolute path to the nix binary
set -euo pipefail

nix_bin="${1:?nix binary path required}"
nix_bin_dir="$(dirname "$nix_bin")"
nix_collect="$nix_bin_dir/nix-collect-garbage"
nix_store="$nix_bin_dir/nix-store"

# Remove old generations for all users + root (aggressive)
if [ -x "$nix_collect" ]; then
  "$nix_collect" -d
else
  "$nix_bin" store gc || true
fi

# Additional GC pass (useful on some setups / older nix)
if [ -x "$nix_store" ]; then
  "$nix_store" --gc || true
else
  "$nix_bin" store gc || true
fi

# Deduplicate store paths to reduce disk usage (can take a bit).
# Prefer modern CLI; fall back to nix-store on older setups.
if ! "$nix_bin" store optimise; then
  if [ -x "$nix_store" ]; then
    "$nix_store" --optimise || true
  fi
fi
