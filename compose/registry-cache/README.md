# Registry-Cache Wiring 🪞

Static configuration that wires the `infinito` runner container to the
`registry-cache` pull-through proxy defined in
[compose.yml](../../compose.yml). The proxy
(`rpardini/docker-registry-proxy`) intercepts every outbound docker
registry pull from `infinito`'s inner dockerd and caches blobs and
manifests so re-deploys, parallel CI shards, and local fresh-purges
do not trigger live registry round-trips.

## Scope 📋

- This directory MUST contain only files consumed by the
  `registry-cache` compose service or its peer `infinito` container.
- The systemd drop-in `proxy.conf` is bind-mounted directly to
  `/etc/systemd/system/docker.service.d/registry-cache-proxy.conf` via
  [compose.yml](../../compose.yml), so changes take effect on the next
  container start without an image rebuild.
- The companion CA-install script lives at
  [scripts/docker/registry-cache-ca.sh](../../scripts/docker/registry-cache-ca.sh)
  because it is called by dockerd's `ExecStartPre`, which expects the
  binary on the runner's `$PATH`. It is bind-mounted to
  `/usr/local/bin/registry-cache-ca.sh`; the file MUST keep its
  git +x bit because bind-mounts preserve host permissions.

## Files 📄

- `proxy.conf`: systemd drop-in for `docker.service`. Sets
  `HTTP_PROXY` / `HTTPS_PROXY` to the proxy and registers the CA-install
  script as `ExecStartPre`.

For the env-variable contract that governs cache size and host paths,
see the Registry Cache section in
[compose.yml.md](../../docs/contributing/artefact/files/compose.yml.md).
