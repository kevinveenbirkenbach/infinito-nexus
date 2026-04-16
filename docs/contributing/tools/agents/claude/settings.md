# Claude Code Settings 🤖

This page documents the permission and runtime configuration in [`.claude/settings.json`](../../../../../.claude/settings.json) and explains the security model that protects the host while keeping agent workflow flowing.
For general agent workflow rules, see [common.md](../common.md).
For the OS-level sandbox configuration that makes this model safe, see [sandbox.md](sandbox.md).
For the Claude Code reference, see [docs.claude.com](https://code.claude.com/docs/en/settings).

## Security Architecture 🛡️

The project relies on **two layers** of protection that work together:

1. **OS-level sandbox** (`sandbox.*` block) — the primary containment. Every Bash command runs inside `bwrap` (Linux) or `sandbox-exec` (macOS) and is confined by filesystem and network rules. The sandbox is fail-closed: if it cannot start, Claude Code refuses to proceed (`failIfUnavailable: true`). Sandbox-escape is disabled (`allowUnsandboxedCommands: false`) so the `dangerouslyDisableSandbox` tool parameter is ignored — there is no "trust me, run me unconfined" path.
2. **Permission lists** (`permissions.{allow,ask,deny}`) — the policy gate that decides whether the agent may attempt a tool call at all. With the sandbox doing the heavy lifting on confinement, the `allow` list deliberately stays minimal: it covers non-Bash tools and trusts `autoAllowBashIfSandboxed: true` to auto-permit Bash inside the sandbox. The `deny` list still applies as an unconditional hard block, and the `ask` list still pauses for operator confirmation.

This split means: contributors do not need to extend the allowlist for every new shell command they want the agent to run. Sandbox confinement bounds the blast radius. The `deny` list catches the small set of operations whose blast radius is destructive even within the sandbox (e.g. `rm -rf .` would erase the repo + `.git/`).

## Permission Model 🔐

Claude Code evaluates each tool call against the lists in [`permissions`](../../../../../.claude/settings.json):

| List | Behavior |
|---|---|
| `allow` | Executes automatically without prompting. |
| `ask` | Pauses and asks the operator for approval before executing. |
| `deny` | Rejects the call unconditionally, even if `allow` would otherwise match. |

`deny` takes precedence over `allow`. `settings.local.json` MAY extend project permissions locally but MUST NOT weaken `deny` rules defined here.

For Bash specifically, `sandbox.autoAllowBashIfSandboxed: true` adds an implicit auto-allow when the sandbox is active. Bash commands therefore run without an explicit `Bash(...)` allowlist entry as long as no `deny` or `ask` rule matches.

## Allow Permissions ✅

The allowlist is intentionally short. With sandboxed Bash auto-allowed, only non-Bash tools and the wildcarded web tools need explicit entries.

| Permission | When | Why | Security |
|---|---|---|---|
| `Read` | Every task that inspects a file. | Core IDE operation. The agent cannot understand code without it. | Scope is limited by `denyRead` in the sandbox configuration (see [sandbox.md](sandbox.md)). Credential directories are never readable. |
| `Edit` | Every task that modifies an existing file. | Core IDE operation. Required for any code change. | Write scope is bounded by `allowWrite` (see [sandbox.md](sandbox.md)). Changes outside `.`, `/tmp`, and `~/.cache/pre-commit` are blocked. |
| `Write` | Every task that creates a new file. | Core IDE operation. Required for scaffolding and new file creation. | Same sandbox boundary as `Edit`. |
| `WebSearch` | Looking up documentation, error messages, or package information. | Allows the agent to resolve unknown APIs and tooling questions without leaving the terminal. | Outbound query only. No local data is uploaded. |
| `WebFetch(domain:*)` | Fetching documentation, repository pages, registry metadata, or any other public web resource. | Replaces the previous explicit per-domain allowlist. The wildcard reflects that web research is a routine, low-risk activity for a sandboxed agent and that maintaining a per-domain list created friction without measurable safety gain. | Read-only HTTP fetches. Credentials in URLs are still discouraged. Egress is bounded by the sandbox network configuration (see [sandbox.md](sandbox.md)) and any host-level firewall. |

### Bash via Sandbox Auto-Allow

Bash commands that match neither `ask` nor `deny` execute automatically because `sandbox.autoAllowBashIfSandboxed: true` treats sandbox confinement as the primary policy gate. There is no per-command `Bash(...)` allowlist to maintain.

This means:

- **No allowlist edits** are needed when introducing new make targets, scripts, or tooling. The sandbox already bounds what they can read, write, and reach over the network.
- **Read-only inspection commands** (`grep`, `find`, `ls`, `cat`, `git log`, `docker ps`, etc.) just work.
- **Mutating commands** that stay inside `allowWrite` (e.g. `make test`, `pip install`, `docker build`) just work.
- **Mutating commands that target paths outside `allowWrite`** (e.g. `mv ~/file /etc/`) fail at the sandbox layer with EROFS.
- **Outbound network calls** are bounded by `sandbox.network.allowedDomains` (currently `*` — see [sandbox.md](sandbox.md)).

The trade-off is documented in [sandbox.md](sandbox.md): convenience and architectural clarity at the cost of relying on the sandbox to be correct. The `deny` list below is what catches the destructive cases the sandbox cannot prevent.

## Ask Permissions ⚠️

These operations pause and require explicit operator approval before executing, even when sandboxed.

| Permission | When | Why approval is required | Security |
|---|---|---|---|
| `git commit*` | Creating a permanent history entry. | The operator MUST review the staged diff and message before committing. | Commits are persistent and visible to all contributors after push. |
| `git push*` | Publishing changes to the remote. | Cannot be undone without a force-push. | Exposes changes to all repository collaborators and CI. |
| `docker run*` | Starting a standalone container outside the compose stack. | Each invocation carries a unique risk profile depending on flags. | Can mount host paths, expose ports, and run privileged containers. |
| `gh api*` | Making direct GitHub REST or GraphQL API calls. | Can modify branch protection, secrets, webhooks, collaborators, and workflow triggers. | Supports arbitrary HTTP methods (`-X POST/PATCH/DELETE`). Each invocation MUST be reviewed individually. |
| `gh workflow run*` | Triggering a CI workflow run on the remote. | Consumes runner minutes, executes with workflow secrets, and produces remotely-visible results. Equivalent in effect to `git push` for triggered runs. | Each invocation MUST be reviewed to confirm the target workflow and inputs. |

## Deny Rules 🚫

These operations are unconditionally blocked, regardless of any `allow` entry or sandbox state. They cover destructive patterns whose blast radius is unacceptable even inside the sandbox (`.` is `allowWrite`, so `rm -rf .` would still erase the working tree and `.git/`).

| Permission | Reason |
|---|---|
| `git push --force*` | Rewrites remote history. Can permanently destroy other contributors' work. |
| `git reset --hard*` | Discards all uncommitted local changes without any recovery path. |
| `git clean*` | Any invocation of `git clean` is blocked. All useful variants (`-f`, `-fd`, `-xfd`) force-delete untracked files with no recovery path; the wildcard covers every flag order. Can silently wipe in-progress work the agent has not yet surfaced to the operator. |
| `git branch -D*` | Force-deletes local branches regardless of merge status. Can destroy unmerged work with no recovery path. |
| `rm -rf*` | Recursive force-delete with no confirmation and no undo. Sandbox `allowWrite` does not protect here because `.` (the repo) is writable; `rm -rf .` would erase the working tree and `.git/`. |
| `sudo*` | Prevents privilege escalation attempts. The sandbox already blocks privileged operations, but denying `sudo` outright avoids accidental approval prompts and makes the intent explicit. |
| `gh workflow enable*` | Re-enabling a workflow can silently restart paused CI (e.g. security scans deliberately disabled during incident response) without operator review. |
| `gh workflow disable*` | Disabling a workflow can silently turn off security-critical CI (CodeQL, security-review, lint gates). Must never be done autonomously. |

## Environment Overrides 🌳

The top-level `env` block sets process environment variables for every Claude Code session. It is currently used to disable GPG signing for agent-created commits via the additive `GIT_CONFIG_COUNT` mechanism:

```json
"env": {
  "GIT_CONFIG_COUNT": "1",
  "GIT_CONFIG_KEY_0": "commit.gpgsign",
  "GIT_CONFIG_VALUE_0": "false"
}
```

| Variable | Effect | Why |
|---|---|---|
| `GIT_CONFIG_COUNT` + `GIT_CONFIG_KEY_0` + `GIT_CONFIG_VALUE_0` | Adds `commit.gpgsign=false` on top of the normal git config stack (system → global → local → env). Local `.git/config` and global `~/.gitconfig` are still consulted for everything else (notably `user.name` and `user.email`), so author identity continues to come from the host. | The sandbox `denyRead: ~/.gnupg` rule blocks GPG access by design — agent commands must never touch private key material. This env override removes the resulting signing failure without weakening the credential-path protection. Agent-authored commits land unsigned; the `Co-Authored-By` trailer documents authorship. |

Future env entries SHOULD follow the same principle: prefer adjusting environment over weakening sandbox `denyRead` or extending `allowWrite`.

## Local Overrides 🖥️

Contributors MAY extend project permissions via `.claude/settings.local.json`. This file is git-ignored and applies only to the local machine.

| Rule | Description |
|---|---|
| MUST NOT weaken `deny` | Local overrides cannot lift unconditional blocks defined in `settings.json`. |
| MUST NOT disable the sandbox | Local overrides MUST NOT set `sandbox.enabled: false`, `sandbox.failIfUnavailable: false`, or `sandbox.allowUnsandboxedCommands: true`. The security model depends on the sandbox being on and fail-closed. |
| Machine-specific entries MUST stay local | Absolute paths, process IDs, and debug tooling MUST NOT be promoted to `settings.json`. |
| Shared permissions SHOULD be promoted | Permissions useful for all contributors SHOULD be added to `settings.json` instead of staying local. |
| Keep overrides minimal | Entries already covered by project-level wildcards or by sandbox auto-allow SHOULD be removed from `settings.local.json`. |
