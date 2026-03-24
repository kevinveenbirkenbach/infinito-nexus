#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_DIR="${REPOSITORY_DIR:-.}"

git -C "${REPOSITORY_DIR}" tag -l 'v*' | sort -V
