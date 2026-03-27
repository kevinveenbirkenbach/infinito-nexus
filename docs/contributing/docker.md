[Back to CONTRIBUTING hub](../../CONTRIBUTING.md)

# Docker and Runtime Commands

Use these commands from the repository root. They are thin `make` wrappers around the Docker build scripts and the local compose stack helpers.

## Image Builds

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Build | `make build` | Builds the local image for the active `INFINITO_DISTRO`. | Use this after Dockerfile changes or whenever you want a fresh local image. |
| Build if missing | `make build-missing` | Builds the image only when it is not already present locally. | Use this for a quick local check when you do not want to rebuild unnecessarily. |
| No-cache build | `make build-no-cache` | Rebuilds the image without Docker cache. | Use this when cache reuse might hide a change or when you are debugging the build. |
| No-cache all distros | `make build-no-cache-all` | Rebuilds the no-cache image for every distro in `DISTROS`. | Use this for release-level validation or when you need to verify all distro variants. |
| Build dependency image | `make build-dependency` | Pulls the `pkgmgr` base image used by the build. | Use this when you want to refresh the base image or debug build inputs. |
| Cleanup CI images | `make build-cleanup` | Removes Docker images created for CI-style build workflows. | Use this when local disk usage grows or old CI images accumulate. |

## Compose Stack

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Start stack | `make up` | Starts the local compose stack and builds the image if it is missing. | Use this to bring the development stack online. |
| Stop stack | `make down` | Stops the compose stack and removes volumes. | Use this when you want a clean shutdown and disposable local state. |
| Pause services | `make stop` | Stops running services without removing volumes. | Use this when you want a fast stop and plan to start the same state again. |
| Restart stack | `make restart` | Stops the stack and starts it again. | Use this after configuration changes or when the stack needs a full restart. |

## Support Targets

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Docker ignore file | `make dockerignore` | Regenerates `.dockerignore` from `.gitignore`. | Use this only when you need to recreate the generated Docker ignore file. |

## Notes

- The commands use the current `INFINITO_DISTRO` setting from the environment.
- `make down` is destructive because it removes volumes; use `make stop` if you want to preserve state.
- `make up` may build missing images automatically, so you often do not need a separate build step for a first start.
- For app-level local deploy flows and end-to-end checks, see [Testing and Validation](testing.md).
