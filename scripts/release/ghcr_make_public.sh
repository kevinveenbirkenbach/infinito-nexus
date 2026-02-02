#!/usr/bin/env bash
set -euo pipefail

# Make mirrored GHCR container packages public.
#
# This script computes the package names from roles/**/config/main.yml (Docker Hub images only),
# using the same mapping logic as the mirror code:
#   - package name:   <prefix>/<image-name-with-slashes-replaced-by-dashes>
#   - e.g. postgis/postgis -> mirror/postgis-postgis
#
# It then PATCHes GitHub's Packages API to set visibility="public".
#
# Requirements:
#  - GH_TOKEN must be set (GitHub token with packages:write)
#  - python3 available (uses repo's cli.mirror.util.iter_role_images)
#
# Usage:
#   GH_TOKEN=... ./scripts/release/ghcr_make_public.sh \
#     --ghcr-namespace kevinveenbirkenbach \
#     --ghcr-prefix mirror \
#     --repo-root .

die() { echo "ERROR: $*" >&2; exit 2; }

GHCR_NAMESPACE=""
GHCR_PREFIX="mirror"
REPO_ROOT="."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ghcr-namespace) GHCR_NAMESPACE="${2:-}"; shift 2 ;;
    --ghcr-prefix)    GHCR_PREFIX="${2:-}"; shift 2 ;;
    --repo-root)      REPO_ROOT="${2:-}"; shift 2 ;;
    -h|--help)
      cat <<'EOF'
Usage:
  ghcr_make_public.sh --ghcr-namespace <user|org> [--ghcr-prefix mirror] [--repo-root .]

Environment:
  GH_TOKEN   GitHub token (needs packages: write)

Example:
  GH_TOKEN=... ./scripts/release/ghcr_make_public.sh \
    --ghcr-namespace kevinveenbirkenbach \
    --ghcr-prefix mirror \
    --repo-root .
EOF
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

[[ -n "${GHCR_NAMESPACE}" ]] || die "--ghcr-namespace is required"
[[ -n "${GH_TOKEN:-}" ]] || die "GH_TOKEN is required (export GH_TOKEN=...)"

echo ">>> Publishing mirrored packages as public"
echo ">>> Namespace: ${GHCR_NAMESPACE}"
echo ">>> Prefix:    ${GHCR_PREFIX}"
echo ">>> Repo root: ${REPO_ROOT}"

cd "${REPO_ROOT}"

tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT

# Compute unique package names (URL-encoded), like: mirror%2Fpostgres
python3 - <<PY >"$tmpfile"
from pathlib import Path
from urllib.parse import quote

from cli.mirror.util import iter_role_images

repo_root = Path(${REPO_ROOT!r}).resolve()
prefix = ${GHCR_PREFIX!r}.strip("/")

pkgs = set()
for img in iter_role_images(repo_root):
    mapped = img.name.replace("/", "-")
    pkgs.add(f"{prefix}/{mapped}")

for pkg in sorted(pkgs):
    print(quote(pkg, safe=""))
PY

count="$(wc -l < "$tmpfile" | tr -d ' ')"
echo ">>> Packages to publish: ${count}"

failures=0

while IFS= read -r pkg_enc; do
  [[ -n "$pkg_enc" ]] || continue
  echo ">>> Set public: ${pkg_enc}"

  # Try user scope first
  if curl -fsS -X PATCH \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/user/packages/container/${pkg_enc}" \
    -d '{"visibility":"public"}' >/dev/null; then
    continue
  fi

  # Fallback to org scope
  if curl -fsS -X PATCH \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/orgs/${GHCR_NAMESPACE}/packages/container/${pkg_enc}" \
    -d '{"visibility":"public"}' >/dev/null; then
    continue
  fi

  echo "!!! Failed to set public: ${pkg_enc} (rights? package missing? namespace mismatch?)" >&2
  failures=$((failures + 1))
done < "$tmpfile"

if [[ "$failures" -gt 0 ]]; then
  echo ">>> Publish step finished with ${failures} failures (best-effort)." >&2
  exit 0
fi

echo ">>> Publish step finished successfully."
