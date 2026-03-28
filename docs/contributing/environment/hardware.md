[Back to Environment](README.md)

# Manage Low-Hardware Resources

Use this guide when you work on a machine with limited CPU, RAM, or disk.

## Goal Hardware

A practical long-term target is:

- 64 GB RAM
- a swapfile about the same size as RAM
- an external SSD with more than 500 GB
- enough room for Docker images, volumes, build cache, and local repositories

If disk space is tight, move Docker data, caches, and your working directory to the SSD.

On Linux, you can move Docker to a different data path:

```json
{
  "data-root": "/mnt/ssd/docker"
}
```

Then restart Docker:

```bash
sudo systemctl restart docker
```

Make sure the mount is available before Docker starts. Otherwise the daemon may fall back to the system drive or fail to start cleanly.

On macOS and Windows, use Docker Desktop settings instead of `daemon.json`.

A same-size swapfile helps absorb memory spikes on Linux. On Windows and macOS, keep enough free disk space available for virtual memory and local caches.

## Load Only What You Need

For a broad stack like the Community Hub, start only the services you actually need. If you are working on Discourse, you do not need Mastodon, Pixelfed, PeerTube, or Friendica in the same session.

The main lever is each role's `config/main.yml`, where Compose services are enabled or disabled:

- use `enabled: true` only for services you actually need
- set `enabled: false` for optional services
- for shared services, also set `shared: false` if they are not needed

Example of a slim local Discourse configuration:

```yaml
compose:
  services:
    discourse:
      enabled: true
    database:
      enabled: true
      shared: true
      type: "postgres"
    redis:
      enabled: true
    oidc:
      enabled: false
      shared: false
    logout:
      enabled: false
    ldap:
      enabled: false
      shared: false
    dashboard:
      enabled: false
    matomo:
      enabled: false
      shared: false
    css:
      enabled: false
```

This is a development profile, not a production target. Enable SSO, LDAP, or analytics only when you need them.

## Test Smarter

On small machines, limit validation to the role you are touching.

For Discourse, start with:

```bash
APP=web-app-discourse make deploy-fresh-purged-app
```

If the local inventory and stack already exist, reuse them:

```bash
APP=web-app-discourse make deploy-reuse-kept-app
```

Use `make deploy-fresh-kept-all` only when you need broad coverage and have enough time and resources.

## Measure Before You Delete

Before cleaning up, check what is actually consuming space:

```bash
docker system df
docker ps -a
docker images
journalctl --disk-usage
df -h
```

That makes it easier to see whether the real issue is Docker, journald, a package cache, or project state.

## Cleanup

The cleanup SPOT is [scripts/purge/README.md](../../../scripts/purge/README.md). Use that page for the canonical entry points.

For the one-time Windows `cleanmgr /sageset:1` setup, set `PURGE_WINDOWS_CLEANMGR_SETUP=true` before you run `make purge-system`.

For related local helpers, see [scripts/tests/deploy/local/purge/README.md](../../../scripts/tests/deploy/local/purge/README.md) and [scripts/tests/deploy/local/reset/README.md](../../../scripts/tests/deploy/local/reset/README.md).

## Further Reading

For the full public article, see [Developing on PCs with Limited Resources](https://s.infinito.nexus/minpcdev).
