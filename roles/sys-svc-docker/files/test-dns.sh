#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Required env (must already be present in the container)
# ------------------------------------------------------------
: "${DNS_IP:?Missing env DNS_IP}"
: "${DOMAIN:?Missing env DOMAIN}"
: "${IP4:?Missing env IP4}"

SUBDOMAIN="foo.${DOMAIN}"
IP4_EXPECTED="${IP4}"

section() {
  echo
  echo "------------------------------------------------------------"
  echo "$1"
  echo "------------------------------------------------------------"
}

ok()   { echo "OK:   $*"; }
fail() { echo "FAIL: $*"; exit 1; }

section "Wait for dockerd (DinD)"
for i in $(seq 1 60); do
  if [ -S /var/run/docker.sock ] && docker info >/dev/null 2>&1; then
    ok "dockerd ready"
    break
  fi
  sleep 1
done

[ -S /var/run/docker.sock ] || fail "docker.sock missing after waiting"
docker info >/dev/null 2>&1 || fail "docker info still failing after waiting"

section "Docker-in-Docker DNS (busybox)"
docker run --rm --dns "${DNS_IP}" busybox:1.36 sh -lc "
  set -e

  test_lookup() {
    name=\"\$1\"
    out=\$(nslookup \"\$name\" 2>&1 || true)
    echo \"\$out\"
    echo \"\$out\" | grep -q \"Address: ${IP4_EXPECTED}\" || {
      echo \"DNS lookup failed for \$name\"
      exit 1
    }
  }

  test_lookup \"${DOMAIN}\"
  test_lookup \"${SUBDOMAIN}\"
"

ok "Inner container DNS works"
