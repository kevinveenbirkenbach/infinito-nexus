[Back to Environment](README.md)

# Manage Low-Hardware Resources

Use this guide when you work on a machine with limited CPU, RAM, or disk.

This repository copy mirrors the full guidance so the most important low-resource practices stay close to the contributing docs.
The public article with the same topic is [Developing on PCs with Limited Resources](https://s.infinito.nexus/minpcdev).

## Quick Checklist

- Keep the local stack minimal and enable only the services you actually need.
- Follow the retry-loop policy in [Iteration](../../agents/action/iteration.md).
- Avoid full-stack validation unless you really need it.
- Move Docker data, build cache, and working copies to fast storage when possible.
- Use a swapfile the same size as RAM on Linux when you want more headroom against spikes.

## Goal Hardware

If you want long-term stability and less friction, this is a solid target:

- 64 GB RAM
- a swapfile the same size as RAM
- an external SSD with more than 500 GB
- enough room for Docker images, volumes, build cache, and local repositories

The SSD is often the cheapest and most effective upgrade. If disk space is tight, move Docker data, caches, and ideally your working directory to that drive.

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

On macOS and Windows, this is usually handled through Docker Desktop settings rather than `daemon.json`.

For swap: on Linux, a swapfile equal to your RAM size is a good buffer against memory spikes, OOM kills, and hard crashes. If you have less RAM, the same idea still helps, but you will need to be even stricter about keeping the stack small. On Windows and macOS, the OS manages virtual memory itself, but free disk space still matters a lot.

## Load Only What You Need

For a broad stack like the Community Hub, it helps a lot not to start everything at once. If you are only working on Discourse, you do not automatically need Mastodon, Pixelfed, PeerTube, or Friendica in the same session.

The main lever is each role's `config/main.yml`. That is where Compose services are enabled or disabled. The rule is simple:

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

This is a development profile, not a production target. If you need to test SSO, LDAP, or analytics, enable those services deliberately. But on weaker hardware, the general rule is: as little as possible, as much as necessary.

At bundle level, the same principle applies. If you are only changing Discourse in the Community Hub, do not start the whole stack unless you need it.

## Test Smarter

On small machines, it helps to limit validation to the one role you are actually touching.

For Discourse, this is usually the best start:

```bash
APP=web-app-discourse make deploy-fresh-purged-app
```

If the local inventory and stack are already in place, this is often the faster iteration loop:

```bash
APP=web-app-discourse make deploy-reuse-kept-app
```

I would only use `make deploy-fresh-kept-all` on weaker hardware if you truly need broad coverage and you have enough time and resources.

## Measure Before You Delete

Before cleaning up, it is worth checking what is actually consuming space:

```bash
docker system df
docker ps -a
docker images
journalctl --disk-usage
df -h
```

That usually makes it much easier to see whether the real issue is Docker, journald, a package cache, or simply the project state.

## Docker Cleanup

First: there is no single `docker prune` command. In practice, people usually mean one of these.

For a single project, this is the first cleanup step:

```bash
docker compose down --volumes --remove-orphans
```

If you need the big cleanup, these are the usual commands:

```bash
docker system prune -a --volumes -f
docker container prune -f
docker image prune -a -f
docker volume prune -f
docker network prune -f
docker builder prune -a -f
docker context prune -f
```

When I use what:

- `docker compose down --volumes --remove-orphans` for one project
- `docker system prune -a --volumes -f` for the big hammer
- `docker builder prune -a -f` when build cache grows too large
- `docker volume prune -f` when old volumes consume space
- `docker image prune -a -f` when old images pile up
- `docker network prune -f` when old networks remain
- `docker context prune -f` when you have many stale Docker contexts

If you use Buildx, add this when needed:

```bash
docker buildx prune -a -f
```

## Repo and Project Cleanup

Inside this repository, these commands help a lot:

```bash
make down
make stop
make clean
make clean-sudo
make build-cleanup
make container-purge-system
make container-irefresh-inventory
```

Quick explanation:

- `make down` stops the stack and removes volumes
- `make stop` stops the stack but keeps the state
- `make clean` removes ignored Git files
- `make clean-sudo` does the same with `sudo`, if root-owned files exist
- `make build-cleanup` removes old CI images
- `make container-purge-system` cleans local deploy artifacts
- `make container-irefresh-inventory` resets the local inventory

If you often switch branches or work on only one role at a time, a disciplined `down` and `clean` routine usually saves more space than trying to recover later with a huge prune.

## What This Repository Automates

The repository already contains cleanup-related roles and helpers that implement the same idea:

- `sys-ctl-cln-docker` handles Docker cleanup and anonymous volumes
- `sys-ctl-cln-disc-space` frees disk space by clearing temp files, package caches, and journald
- `sys-cleanup` performs cross-distro cache cleanup
- `svc-opt-swapfile` creates a swapfile and defaults its size to the system RAM

Those roles are useful to keep in mind when you want automation instead of manual cleanup.

## Linux

### Common

Use these on most Linux setups before you go distro-specific:

```bash
docker compose down --volumes --remove-orphans
docker system prune -a --volumes -f
docker builder prune -a -f
docker image prune -a -f
docker volume prune -f
docker network prune -f
docker context prune -f
journalctl --vacuum-size=100M
journalctl --vacuum-time=3h
pip cache purge
npm cache clean --force
yarn cache clean
go clean -cache -modcache
cargo clean
flatpak uninstall --unused -y
```

### Arch

```bash
sudo pacman -Scc --noconfirm
```

### Debian / Ubuntu

```bash
sudo apt-get clean
sudo apt-get autoremove --purge -y
```

### Fedora / CentOS

```bash
sudo dnf clean all
sudo yum clean all
```

This matches the general idea used by the repository's cleanup roles: keep package caches, tool caches, temp files, and journald under control.

## macOS

On macOS, focus on Docker Desktop and Homebrew:

```bash
brew cleanup --prune=all
brew autoremove
docker system prune -a --volumes -f
docker builder prune -a -f
```

If you follow the repo setup, macOS works best when the stack runs in a Linux environment such as Lima. In that case, the same general rule applies: keep Docker and build caches small, and place the Docker disk location on a larger drive if possible.

## Windows

On Windows, the most reliable setup is WSL2. In practice, that means:

- do Docker cleanup inside WSL2 or directly via the Docker CLI
- use Windows-side cleanup tools for host cleanup
- run `wsl --shutdown` when you want memory returned to the host

Useful Windows commands:

```powershell
docker system prune -a --volumes -f
docker builder prune -a -f
wsl --shutdown
cleanmgr /sageset:1
cleanmgr /sagerun:1
DISM /Online /Cleanup-Image /StartComponentCleanup
```

`cleanmgr /sageset:1` is typically configured once as Administrator. After that, `cleanmgr /sagerun:1` reuses the same cleanup profile.

If you are working in WSL2, you can also use the Linux commands from the Linux section inside the WSL shell. That is often the cleanest approach, because the Docker workload usually lives there.

## Standard Routine

When the machine starts feeling tight, I usually do this:

1. Start only the role I actually need.
2. Stop the stack cleanly with `make down` or `docker compose down --volumes --remove-orphans`.
3. Clear Docker cache with `docker builder prune -a -f` and `docker system prune -a --volumes -f`.
4. Clean host caches depending on the operating system.
5. Start fresh again.

It sounds simple, but that is exactly what keeps smaller machines usable over time.

If you have to develop on limited hardware, the best strategy is not "more power", but "less load per session".

## Further Reading

For the full public article, see [Developing on PCs with Limited Resources](https://s.infinito.nexus/minpcdev).

Use the operating-system-specific cleanup commands above when you need more disk space.
