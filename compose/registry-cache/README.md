# Registry-Cache Wiring 🪞

Static configuration consumed by the `registry-cache` compose service and bind-mounted into the `infinito` runner.

For services, activation, coverage, and operations of the local cache stack, see [cache.md](../../docs/contributing/environment/cache.md).

## Files 📄

- `proxy.conf`: systemd drop-in for `docker.service`. Sets `HTTP_PROXY`/`HTTPS_PROXY` to the proxy and registers [registry-ca.sh](../../scripts/docker/cache/registry-ca.sh) as `ExecStartPre`.
