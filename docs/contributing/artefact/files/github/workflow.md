# GitHub workflow files 🔄

This page is the SPOT for repository rules that govern GitHub Actions workflow files under `.github/workflows/`.
For the catalog of every workflow (description, triggers, inputs) see [workflows.md](../../../tools/github/actions/workflows.md).
For the script placement rule that applies to extracted shell helpers, see [scripst.md](../../scripst.md).

## Naming 🏷️

Every workflow MUST follow the schema `"[Emoji] Category: Subject (Qualifier)"`.

- You MUST quote the `name:` value in double quotes because the colon (`:`) in the name is a reserved YAML character.
- You MUST place the emoji before the category, never after.
- You MUST NOT add emojis to `docs/agents/` files, but workflow `name:` fields are not agent files and MUST use emojis.
- The qualifier in parentheses is OPTIONAL. Use it only when two workflows share the same category and subject.

### Emoji legend 📋

| Emoji | Category | Used for |
|---|---|---|
| `🔄` | Update / Sync | Automated version or dependency updates |
| `🪞` | Mirror | Image mirroring between registries |
| `🧹` | Images | Image cleanup and pruning |
| `🐳` | Build | Docker image builds |
| `🔍` | Lint | Static analysis and linting |
| `🔒` | Scan | Security scanning |
| `⚡` | CI | CI entry points (push, pull request, manual) |
| `🎵` | CI | CI orchestration and coordination workflows |
| `🚫` | Cancel | Run cancellation on PR close or branch delete |
| `🧪` | Test | Code tests (unit, integration, lint) |
| `💻` | Test | Development environment tests |
| `💬` | Test | DNS and network resolution tests |
| `📦` | Test | Deployment tests |
| `📥` | Test | Installation tests |
| `🚀` | Release | Version release workflows |

### Examples ✅

```yaml
name: "🧪 Test: Code (Integration)"
name: "🪞 Mirror: Docker Hub → GHCR (only missing)"
name: "🚫 Cancel: PR Runs on Close"
```

## Shell execution 📜

- Multi-line shell logic in workflow `run:` blocks MUST be extracted into dedicated `.sh` files under `scripts/`.
- Workflow files MUST call those extracted `.sh` entry points instead of embedding longer shell programs inline.
- Short single-command invocations MAY stay inline when they do not contain meaningful control flow.
- Inline shell in workflow files SHOULD stay limited to small command calls, environment wiring, or direct script invocation.

## Disk space 💾

Deploy test workflows use the `jlumbroso/free-disk-space` action to reclaim runner space before Docker pulls start. Because the actual deploy runs **inside** the `infinito` container, the host's language toolchains, build packages, and default Docker layer cache are all dead weight and MUST be reclaimed aggressively.

| Option | Value | Reason |
|---|---|---|
| `tool-cache` | `true` | Deploy runs inside the `infinito` container; host Node/Python/Go/Ruby toolchains go unused |
| `android` | `true` | Android SDK is never needed; safe to remove |
| `dotnet` | `true` | .NET SDK is never needed; safe to remove |
| `haskell` | `true` | Haskell toolchain is never needed; safe to remove |
| `large-packages` | `true` | Ansible, pip and gcc run **inside** the container, not on the host |
| `docker-images` | `true` | Matrix jobs don't share a Docker layer cache; each runner pulls its own `infinito` image |
| `swap-storage` | `true` | Default swap file is replaced by `pierotofy/set-swap-space` (see below) |

Set an option back to `false` only when a new host-side step in the same workflow genuinely needs the removed payload.

## Swap 💾

Deploy test workflows enlarge host swap via [enlarge_swap.sh](../../../../../scripts/github/enlarge_swap.sh) to absorb transient memory spikes (e.g. PeerTube plugin install [#162](https://github.com/infinito-nexus/core/issues/162)) that would otherwise trip the host OOM-killer on the 16 GB GitHub-hosted runner.

The script **prefers `/`** for deterministic placement and falls back to `/mnt` only when `/` does not have enough headroom. Preferring `/` avoids surprises from runners where `/mnt` is unexpectedly pre-populated (larger-runner images, custom Docker-data-root relocations, self-hosted setups).

Swap size is computed dynamically: `free(/) - buffer`. The buffer reserves space for nested Docker layers, the checkout, and the runner cache. With the aggressive `free-disk-space` options above, a ~25 GB buffer typically leaves a 25–30 GB swapfile on `ubuntu-latest`, which is far more than any workload the deploy jobs currently trigger.

| Argument | Default | Reason |
|---|---|---|
| `buffer-gb` (positional) | `25` | Reserves headroom for nested Docker data, checkout and runtime state; pass a smaller value only when you know the job footprint shrinks |

Workflow step invocation:

```yaml
- name: Enlarge swap space
  shell: bash
  run: ./scripts/github/enlarge_swap.sh
```

Ordering:

- Swap step MUST run **after** `actions/checkout` because the script lives inside the repo.
- Swap step SHOULD run **after** `jlumbroso/free-disk-space` so the reclaimed disk on `/` is also a candidate target when `/mnt` is crowded.
- Swap step MUST run **before** any `make up` / container build step so the expanded swap is active when heavy-allocation work begins.

Swap is a host-kernel resource; see [svc-opt-swapfile](../../../../../roles/svc-opt-swapfile/) for why the in-stack swap role is intentionally skipped inside containers.

## Separation of concerns 🧩

- GitHub workflow YAML MUST describe orchestration, permissions, triggers, inputs, and step order.
- Reusable shell behavior MUST live in script files, not in repeated workflow `run:` blocks.
- Non-shell helper logic MUST NOT be embedded as ad-hoc shell blobs inside workflow files.
