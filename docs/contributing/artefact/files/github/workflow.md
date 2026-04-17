# GitHub workflow files 🔄

This page is the SPOT for repository rules that govern GitHub Actions workflow files under `.github/workflows/`.
For the catalog of every workflow (description, triggers, inputs) see [actions.md](../../../tools/actions.md).
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

Deploy test workflows use the `jlumbroso/free-disk-space` action to reclaim runner space before Docker pulls start.

| Option | Value | Reason |
|---|---|---|
| `android` | `true` | Android SDK is never needed; safe to remove |
| `dotnet` | `true` | .NET SDK is never needed; safe to remove |
| `haskell` | `true` | Haskell toolchain is never needed; safe to remove |
| `large-packages` | `false` | Can remove build tools (gcc, Python headers) required by pip/Ansible |
| `docker-images` | `false` | Can remove cached layers reused between deploy steps |
| `swap-storage` | `false` | Disabling swap can cause OOM for memory-intensive services (e.g. Keycloak) |
| `tool-cache` | `false` | Runner tool cache may be needed by subsequent steps |

Only options that are **guaranteed unused** MUST be set to `true`.
When in doubt, keep the option at `false`.

## Separation of concerns 🧩

- GitHub workflow YAML MUST describe orchestration, permissions, triggers, inputs, and step order.
- Reusable shell behavior MUST live in script files, not in repeated workflow `run:` blocks.
- Non-shell helper logic MUST NOT be embedded as ad-hoc shell blobs inside workflow files.
