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

Alternatively, set the `SERVICES_DISABLED` environment variable before creating the inventory to disable services automatically across all applications without editing any file:

```bash
SERVICES_DISABLED="matomo" make deploy-fresh-purged-app APPS=web-app-discourse
```

This sets `enabled: false` and `shared: false` for every listed service in the generated inventory. See [variables.md](variables.md) for details.

| Service | Required | What it provides | Effect of disabling | Safe to disable when |
|---|---|---|---|---|
| `oidc` | 🟠 | Single sign-on via Keycloak | App falls back to local login | You are not testing SSO/OIDC flows |
| `ldap` | 🟠 | Central user directory via OpenLDAP | App uses its own local user store | You are not testing LDAP/user sync |
| `matomo` | 🔴 | Analytics tracking | No usage statistics collected — usually no functional impact | You are not testing analytics integration |
| `css` | 🟠 | Custom theming/branding stylesheet | App uses its default upstream theme | You are not testing visual customization |
| `logout` | 🟠 | Shared logout endpoint across apps | Single sign-out does not propagate | You are not testing cross-app logout |
| `dashboard` | 🟠 | Central navigation hub | App is not reachable via the dashboard | You access the app directly by URL |
| `redis` | 🟢 | In-memory cache and session store | Caching and queuing are disabled | The app does not require sessions or queues (rarely safe) |
| `database` | 🟢 | Shared relational database (MariaDB/Postgres) | App cannot persist data | **Never disable** — required by almost every app |

**Legend:**

- 🟢 Required — cannot be disabled.
- 🟠 Optional — can be disabled, reduces functionality.
- 🔴 Safe to disable — usually no functional impact.

This is a development profile, not a production target. Enable SSO, LDAP, or analytics only when you need them.

## Test Smarter

On small machines, limit validation to the role you are touching.

For Discourse, start with:

```bash
SERVICES_DISABLED="matomo" APPS=web-app-discourse make deploy-fresh-purged-app
```

If the local inventory and stack already exist, reuse them:

```bash
SERVICES_DISABLED="matomo" APPS=web-app-discourse make deploy-reuse-kept-app
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

The cleanup SPOT is the [purge guide](../../../scripts/system/purge/README.md). Use that page for the canonical entry points.

For the one-time Windows `cleanmgr /sageset:1` setup, set `PURGE_WINDOWS_CLEANMGR_SETUP=true` before you run `make purge-system`.

For related local helpers, see the [local purge guide](../../../scripts/tests/deploy/local/purge/README.md) and the [local reset guide](../../../scripts/tests/deploy/local/reset/README.md).

## Discussion

Discuss this topic in the related [forum article](https://s.infinito.nexus/minpcdev).
