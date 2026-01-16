#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Load environment (Single Source of Truth)
# ------------------------------------------------------------
ENV_FILE="${ENV_FILE:-env.ci}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: env file not found: ${ENV_FILE}"
  exit 1
fi

# Export all variables from env file
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

# ------------------------------------------------------------
# Required variables (fail hard if missing)
# ------------------------------------------------------------
: "${DNS_IP:?Missing DNS_IP in env file}"
: "${DOMAIN:?Missing DOMAIN in env file}"
: "${IP4:?Missing IP4 in env file}"

SUBDOMAIN="foo.${DOMAIN}"
IP4_EXPECTED="${IP4}"
INFINITO_CONTAINER="${INFINITO_CONTAINER:?Missing INFINITO_CONTAINER env (e.g. infinito_nexus_arch)}"

# ------------------------------------------------------------
# Output helpers
# ------------------------------------------------------------
section() {
  echo
  echo "------------------------------------------------------------"
  echo "$1"
  echo "------------------------------------------------------------"
}

ok()   { echo "OK:   $*"; }
warn() { echo "WARN: $*"; }
fail() { echo "FAIL: $*"; exit 1; }

# ------------------------------------------------------------
# Banner
# ------------------------------------------------------------
echo "============================================================"
echo " DNS TEST SUITE"
echo "============================================================"
echo "ENV_FILE   = ${ENV_FILE}"
echo "DNS_IP     = ${DNS_IP}"
echo "DOMAIN     = ${DOMAIN}"
echo "SUBDOMAIN  = ${SUBDOMAIN}"
echo "EXPECT IP  = ${IP4_EXPECTED}"
echo "INFINITO   = ${INFINITO_CONTAINER}"
echo

# ------------------------------------------------------------
# Host -> CoreDNS direct
# ------------------------------------------------------------
section "Host -> CoreDNS (direct queries)"

if command -v dig >/dev/null 2>&1; then
  a1="$(dig @${DNS_IP} "${DOMAIN}" A +short | head -n1 || true)"
  a2="$(dig @${DNS_IP} "${SUBDOMAIN}" A +short | head -n1 || true)"

  [[ "${a1}" == "${IP4_EXPECTED}" ]] \
    && ok "${DOMAIN} A -> ${a1}" \
    || fail "${DOMAIN} A failed (got '${a1}')"

  [[ "${a2}" == "${IP4_EXPECTED}" ]] \
    && ok "${SUBDOMAIN} A -> ${a2}" \
    || fail "${SUBDOMAIN} A failed (got '${a2}')"
else
  warn "dig not found on host — skipping host direct DNS tests"
fi

# ------------------------------------------------------------
# CoreDNS container
# ------------------------------------------------------------
section "CoreDNS container status"

if docker ps --filter name=infinito-coredns --format '{{.Names}}' | grep -q infinito-coredns; then
  docker ps --filter name=infinito-coredns --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
  docker logs --tail=10 infinito-coredns || true
  ok "CoreDNS container is running"
else
  fail "CoreDNS container not running"
fi

# ------------------------------------------------------------
# Infinito outer container DNS
# ------------------------------------------------------------
section "Infinito container (outer) DNS"

docker exec "${INFINITO_CONTAINER}" sh -lc "
  set -e

  echo '>>> /etc/resolv.conf'
  cat /etc/resolv.conf || true
  echo

  echo '>>> getent hosts'
  h1=\$(getent hosts ${DOMAIN} | awk '{print \$1}' || true)
  h2=\$(getent hosts ${SUBDOMAIN} | awk '{print \$1}' || true)

  echo \"${DOMAIN} -> \${h1}\"
  echo \"${SUBDOMAIN} -> \${h2}\"

  [[ \"\${h1}\" = \"${IP4_EXPECTED}\" ]] || exit 11
  [[ \"\${h2}\" = \"${IP4_EXPECTED}\" ]] || exit 12
"

ok "Outer container DNS works"

# ------------------------------------------------------------
# Docker-in-Docker (inner container) DNS via busybox
# ------------------------------------------------------------
section "Docker-in-Docker (inner container) DNS"

docker exec "${INFINITO_CONTAINER}" sh -lc "
  set -e

  docker run --rm --dns ${DNS_IP} busybox:1.36 sh -lc '
    echo \"=== resolv.conf ===\"
    cat /etc/resolv.conf || true
    echo

    test_lookup() {
      name=\"\$1\"
      out=\$(nslookup \"\$name\" 2>&1 || true)
      echo \"\$out\"

      echo \"\$out\" | grep -q \"Address: ${IP4_EXPECTED}\" || {
        echo \"DNS lookup failed for \$name\"
        exit 1
      }
    }

    echo \"=== nslookup A ===\"
    test_lookup ${DOMAIN}
    test_lookup ${SUBDOMAIN}

    echo
    echo \"(AAAA queries intentionally ignored)\"
  '
"

ok "Inner container DNS works"

# ------------------------------------------------------------
# DONE
# ------------------------------------------------------------
section "DONE"
echo "DNS chain is fully functional:"
echo "Host -> CoreDNS -> Outer container -> Inner container"
