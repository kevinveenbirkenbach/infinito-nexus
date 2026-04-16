# Claude Code Sandbox 🏖️

This page documents the OS-level sandbox configuration for Claude Code. The relevant keys live under `sandbox` in [`.claude/settings.json`](../../../../../.claude/settings.json). Sandboxing runs **in addition to** the `allow`/`ask`/`deny` permission lists described in [settings.md](settings.md); it does not replace them.

## Activation 🟢

The sandbox is activated unconditionally via `"sandbox": { "enabled": true }`. This means filesystem restrictions below are enforced **at every session**, not only when the operator manually switches into sandbox permission mode. Write scope and read restrictions are enforced by the OS-level sandbox, independent of the `allow`/`ask`/`deny` permission lists. Those lists remain in force as a second line of defence for non-filesystem concerns (network, destructive git operations, privilege escalation).

## Fail-Closed on Missing Backend 🔒

The settings file additionally sets `"sandbox": { "failIfUnavailable": true }`. This prevents a dangerous false-security state: if the OS-level sandbox backend (e.g. `bwrap` on Linux, `sandbox-exec` on macOS) is missing or non-functional, Claude Code would otherwise silently fall back to no sandboxing while `autoAllowBashIfSandboxed` continues to auto-approve commands as if they were confined. With `failIfUnavailable: true`, Claude Code refuses to proceed in that situation, forcing the operator to install the missing backend or explicitly downgrade the policy before any command runs. Contributors on systems without a working sandbox backend MUST install the appropriate binary (`sudo apt install bubblewrap` on Debian-based Linux, preinstalled on macOS) rather than weakening this flag locally.

## Write Scope ✍️

The agent MAY write to `.` (the repository root) and `/tmp`. All other paths are read-only by default. `/tmp` is the **only** location outside the repository where transient agent output (downloaded logs, scratch files, intermediate artefacts) MAY be written; see the *Temporary Files* rule in [`AGENTS.md`](../../../../../AGENTS.md).

## Read Restrictions 🚫

The following directories are never readable, even if a task explicitly requests access:

| Path | What it protects |
|---|---|
| `~/.ssh` | SSH private keys. |
| `~/.gnupg` | GPG keys and keyrings. |
| `~/.kube` | Kubernetes cluster credentials. |
| `~/.aws` | AWS access keys and configuration. |
| `~/.config/gcloud` | Google Cloud service account credentials. |
