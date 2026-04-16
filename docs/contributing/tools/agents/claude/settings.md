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

The allowlist covers non-Bash tools and the wildcarded web tools. Read-only `gh api` calls (default GET, no `-X`/`--method`) are not listed explicitly: they match no `ask` or `deny` rule and therefore execute via sandbox auto-allow without prompting.

| Permission | When | Why | Security |
|---|---|---|---|
| `Read` | Every task that inspects a file. | Core IDE operation. The agent cannot understand code without it. | Scope is limited by `denyRead` in the sandbox configuration (see [sandbox.md](sandbox.md)). Credential directories are never readable. |
| `Edit` | Every task that modifies an existing file. | Core IDE operation. Required for any code change. | Write scope is bounded by `allowWrite` (see [sandbox.md](sandbox.md)). Changes outside `.`, `/tmp`, and `~/.cache/pre-commit` are blocked. |
| `Write` | Every task that creates a new file. | Core IDE operation. Required for scaffolding and new file creation. | Same sandbox boundary as `Edit`. |
| `WebSearch` | Looking up documentation, error messages, or package information. | Allows the agent to resolve unknown APIs and tooling questions without leaving the terminal. | Outbound query only. No local data is uploaded. |
| `WebFetch(domain:*)` | Fetching documentation, repository pages, registry metadata, or any other public web resource. | Replaces the previous explicit per-domain allowlist. The wildcard reflects that web research is a routine, low-risk activity for a sandboxed agent and that maintaining a per-domain list created friction without measurable safety gain. | Read-only HTTP fetches. Credentials in URLs are still discouraged. Egress is bounded by the sandbox network configuration (see [sandbox.md](sandbox.md)) and any host-level firewall. |

### Bash via Sandbox Auto-Allow

Bash commands that match neither `ask` nor `deny` execute automatically because `sandbox.autoAllowBashIfSandboxed: true` treats sandbox confinement as the primary policy gate. For the overwhelming majority of commands there is no per-command `Bash(...)` allowlist to maintain.

This means:

- **No allowlist edits** are typically needed when introducing new make targets, scripts, or tooling. The sandbox already bounds what they can read, write, and reach over the network.
- **Read-only inspection commands** (`grep`, `find`, `ls`, `cat`, `git log`, `docker ps`, etc.) just work.
- **Mutating commands** that stay inside `allowWrite` (e.g. `make test`, `pip install`, `docker build`) just work.
- **Mutating commands that target paths outside `allowWrite`** (e.g. `mv ~/file /etc/`) fail at the sandbox layer with EROFS.
- **Outbound network calls** are bounded by `sandbox.network.allowedDomains` (currently `*` — see [sandbox.md](sandbox.md)).

The trade-off is documented in [sandbox.md](sandbox.md): convenience and architectural clarity at the cost of relying on the sandbox to be correct. The `deny` list below is what catches the destructive cases the sandbox cannot prevent.

### Explicit Bash Allow Entries

A small number of Bash allow entries exist as targeted workarounds for command shapes where sandbox auto-allow does not fire reliably (notably: leading env-variable assignments, output redirections, and `&&`-chained subcommands that each need their own match).

| Permission | When | Why | Security |
|---|---|---|---|
| `XDG_CACHE_HOME=/tmp/* gh run view *` | Fetching CI run / job logs with the `gh` CLI cache relocated into `/tmp`. | `gh run view` is read-only, but invocations in practice combine an `XDG_CACHE_HOME=` env prefix (so the cache lands inside `allowWrite`) with a `> /tmp/...` redirect, which is not reliably covered by auto-allow. The wildcards accept any cache subdirectory under `/tmp/` and any run ID / flag combination. | Read-only GitHub API call. Cache and redirect targets are constrained to `/tmp/` by the `XDG_CACHE_HOME=/tmp/*` prefix and sandbox `allowWrite`. Outbound network bounded by `sandbox.network.allowedDomains`. |
| `gh run list *` | Listing recent CI runs, typically filtered by branch / workflow and formatted via `--json` + `--jq`. | `gh run list` is read-only, but real invocations embed a `--jq '... | select(...) | ...'` expression. The `|` characters inside the jq string confuse the non-quote-aware auto-allow parser, which treats them as shell pipes and fails to match. A single entry covers every flag/`--jq` combination. | Read-only GitHub API call. No filesystem mutation. Outbound network bounded by `sandbox.network.allowedDomains`. |
| `grep *` | Scanning one or many files for regex patterns from the shell. | Claude is instructed in [CLAUDE.md](../../../../../CLAUDE.md) to prefer a single flat `grep` over `for`/`while` loops for multi-file scans; this entry makes that flat-form always-allowed, so the agent can follow the guidance without a prompt. Shell loops around per-file `grep` calls fall outside auto-allow and should be avoided. | Read-only filesystem scan. No mutation, no network. Read scope is still bounded by `denyRead` (see [sandbox.md](sandbox.md)). |
| `wc *` | Counting lines / words / bytes in logs or intermediate files, typically chained after another read-only call via `&&`. | `&&` splits the command line into independently-checked parts, so the right-hand side needs its own allow entry even when the left-hand side already matches. The whole `wc` namespace is read-only regardless of flag (`-l`, `-w`, `-c`, `-m`), so the wildcard is kept broad. | Read-only file inspection. No filesystem mutation, no network. |

## Ask Permissions ⚠️

These operations pause and require explicit operator approval before executing, even when sandboxed.

| Permission | When | Why approval is required | Security |
|---|---|---|---|
| `git commit*` | Creating a permanent history entry. | The operator MUST review the staged diff and message before committing. | Commits are persistent and visible to all contributors after push. |
| `git push*` | Publishing changes to the remote. | Cannot be undone without a force-push. | Exposes changes to all repository collaborators and CI. |
| `docker run*` | Starting a standalone container outside the compose stack. | Each invocation carries a unique risk profile depending on flags. | Can mount host paths, expose ports, and run privileged containers. |
| `gh api * -X *` / `gh api * --method *` | Any explicit non-GET HTTP verb against the GitHub API. | The default `gh api` verb is GET (read-only). Specifying `-X` or `--method` always indicates a write — POST/PATCH/DELETE/PUT — so the prompt forces a per-call review. PUT and DELETE are blocked outright by `deny`; POST and PATCH land here. | Captures every mutating call regardless of endpoint. The DELETE/PUT-specific deny rules below take precedence and reject those verbs unconditionally. |
| `gh api enterprises/*:*` | Any enterprise-scoped API call. | Enterprise endpoints administer org membership, billing, and policy across multiple orgs. | Reviewer MUST confirm the enterprise slug and intended scope. |
| `gh api orgs/*:*` | Any organization-scoped API call. | Org endpoints govern membership, teams, and org-wide settings. | Reviewer MUST confirm the org and the specific endpoint. |
| `gh api repos/*/actions/permissions*:*` | Reading or mutating Actions permissions on a repo. | Toggles whether forks may run workflows, restricts the action allowlist, and gates repo-level CI policy. | Reviewer MUST confirm the policy delta before approval. |
| `gh api repos/*/actions/workflows/*/dispatches:*` | Triggering a workflow via `workflow_dispatch`. | Equivalent in effect to `gh workflow run` — runs CI with workflow secrets and produces remotely-visible results. | Reviewer MUST confirm the workflow ref and inputs payload. |
| `gh api repos/*/branches/*/protection*:*` | Reading or mutating branch protection on a specific branch. | Branch protection gates pushes, merges, and required checks. PUT is already blocked unconditionally; this pattern catches GET-audit and explicit-PATCH paths. | Reviewer MUST confirm the rule delta. |
| `gh api repos/*/environments*:*` | Reading or mutating Actions environments. | Environments gate deployment secrets and required reviewers; weakening them exposes secrets to additional workflows. | Reviewer MUST confirm the environment and gating change. |
| `gh api repos/*/hooks*:*` | Reading or mutating repository webhooks. | Hooks deliver events to external systems; misconfiguration can leak data or break integrations. | Each call MUST be reviewed for target URL and event scope. |
| `gh api repos/*/releases*:*` | Reading or mutating GitHub releases. | Release creation and asset uploads are user-visible publishing actions. | Reviewer MUST confirm the tag and asset payload before approval. |
| `gh api repos/*/rulesets*:*` | Reading or mutating branch/tag rulesets (branch protection successor). | Rulesets gate merges and pushes; weakening them affects every contributor. | Each call MUST be reviewed for the rule scope and required-checks impact. |
| `gh api teams/*:*` | Any team-scoped API call. | Team endpoints govern membership and permission grants. | Reviewer MUST confirm the team and intended change. |
| `gh * <verb>*` (archive, cancel, close, comment, create, delete, develop, edit, fork, link, lock, pin, ready, rename, reopen, rerun, review, unlink, unlock, unpin, upload) | Any `gh` CLI invocation whose second token is a known mutating verb. | The wildcard in the namespace slot collapses 21 mutating verbs across `gh issue/pr/release/repo/ruleset/run/cache/gist/label/project/…` into a single rule per verb. Future namespaces that ship the same verb (e.g. a hypothetical `gh discussion lock`) are caught automatically — explicit per-namespace lists rot as the `gh` CLI grows. | Read-only subcommands (`view`, `list`, `status`, `diff`, `checks`, `watch`, `download`, `clone`) do not match and remain auto-allowed via the sandbox, mirroring the GET-vs-mutation split used for `gh api`. The `deny` rules above take precedence for the highest-blast verbs (e.g. `gh repo delete`, `gh secret *`, `gh ssh-key *`). |
| `gh * field-*` / `gh * item-*` / `gh * mark-template*` / `gh * unmark-template*` | Compound subcommands (e.g. `gh project item-create`, `gh project field-delete`, `gh project mark-template`). | The single-token `gh * <verb>*` patterns above only match when the third token starts with the verb. Compound names like `item-create` or `mark-template` slip through because the third token is the full compound, not the bare verb. These rules close that gap for Projects v2 mutations namespace-wide. | Catches all current and future compound-verb mutations without requiring per-verb enumeration. |
| `gh auth *` | Any `gh auth` subcommand (login, logout, refresh, setup-git, status, switch, token). | Whole namespace asked: `logout` is operator-scope DoS; `token` prints the OAuth/PAT to stdout where it would land in the transcript permanently if approved (operator MUST decline unless they explicitly want the token captured); `switch` silently changes the active identity; `setup-git` rewrites global git config; `login`/`refresh`/`status` are lower-risk but kept inside the same gate for symmetry. The trade-off vs. an explicit `deny` on `logout`/`token` is that approval is now a single click — operators must read the prompt before tapping through. | Reviewer MUST confirm intent for every invocation; in particular `gh auth token` MUST be declined unless the operator deliberately wants the token in the transcript. |
| `gh codespace *` | Any codespace subcommand (create, ssh, cp, delete, ports, …). | Codespaces are billable, persistent VMs with full repo + secret access; `ssh`/`cp` open a remote shell or move files in/out. The whole namespace is asked because even read commands (`list`, `view`) interact with billable infrastructure. | Each invocation MUST be reviewed individually for billing + data-flow impact. |
| `gh config set*` | Sets a `gh` CLI config key. | `gh config set editor /tmp/evil.sh` plants a binary that runs the next time any `gh` subcommand opens an editor (e.g. `gh issue create` without `--body`) — a deferred-execution backdoor that survives the current session. Persistent CLI config belongs to a deliberate operator decision. | Reviewer MUST confirm the key and value, especially for `editor`, `pager`, `git_protocol`. |
| `gh label clone*` | Copies all labels from one repository into another. | Mutation against the destination repo. Verb `clone` is not in the wildcard list because it is otherwise read-only-ish (e.g. `gh repo clone` is just a git clone). | Reviewer MUST confirm both source and destination repos. |
| `gh pr checkout*` | Switches the local working tree to a PR branch. | Does not check for uncommitted changes by default — silently overwrites them. The risk is to local state, not remote, but the loss is unrecoverable. | Reviewer MUST confirm the working tree is clean (or stashed) before approving. |
| `gh project copy*` | Duplicates an entire Projects v2 board. | Verb `copy` is not in the wildcard list. The duplicate is created under the operator's identity and may be public-by-default depending on org settings. | Reviewer MUST confirm the source/destination owners and visibility. |
| `gh repo set-default*` | Sets the default repository for `gh` invocations in the current directory. | Mutates per-directory `gh` config; subsequent ambiguous `gh pr/issue/run` calls would silently target the new default, which can mis-route mutations. Verb `set-default` is not in the wildcard list. | Reviewer MUST confirm the new default repository. |
| `gh repo sync*` | Syncs a fork against its upstream. | Pulls upstream commits into the fork (the operator's repo). Verb `sync` is not in the wildcard list because `gh repo clone`-style reads use related verbs that should remain frictionless. | Reviewer MUST confirm the source/destination repos and that the local working tree tolerates the sync. |
| `gh workflow run*` | Triggering a CI workflow run on the remote. | Consumes runner minutes, executes with workflow secrets, and produces remotely-visible results. Equivalent in effect to `git push` for triggered runs. The verb is `run`, which is not in the wildcarded mutating-verb list above, so it needs its own entry. | Each invocation MUST be reviewed to confirm the target workflow and inputs. |

## Deny Rules 🚫

These operations are unconditionally blocked, regardless of any `allow` entry or sandbox state. They cover destructive patterns whose blast radius is unacceptable even inside the sandbox (`.` is `allowWrite`, so `rm -rf .` would still erase the working tree and `.git/`).

| Permission | Reason |
|---|---|
| `gh api * -X DELETE *` / `gh api * --method DELETE *` | DELETE is irreversible from the API surface — deleting a release, branch ref, deploy key, or webhook destroys data with no undo. Both `-X` and `--method` spellings are blocked so neither shorthand slips through. |
| `gh api * -X PUT *` / `gh api * --method PUT *` | PUT replaces a resource wholesale. On endpoints like branch protection or rulesets, a PUT silently overwrites the entire policy with whatever payload is sent — partial JSON drops every unspecified field. PATCH (the merge variant) still goes through `ask`. |
| `gh api * /actions/secrets*:*` | Touches GitHub Actions secrets — reading metadata, creating, updating, or deleting. Even GETs leak secret names; mutations rotate credentials CI depends on. Out-of-band secret management only. |
| `gh api repos/*/actions/variables*:*` | Touches Actions variables. Variables are unencrypted secrets-lite — workflows read them like secrets, and they are equally load-bearing for CI. Out-of-band variable management only. |
| `gh api repos/*/collaborators*:*` | Reads or mutates repository collaborator membership. Mutations escalate access; even GETs leak the contributor list. Access changes belong to a human reviewer. |
| `gh api repos/*/keys*:*` | Reads or mutates repository deploy keys. Deploy keys are full-power repo-auth credentials — adding one creates a persistent backdoor; removing one breaks deployments. Manage out-of-band only. |
| `gh api repos/*/pulls/*/merge:*` | Merges a pull request via API, bypassing the `gh pr merge` confirmation flow. Merges are destructive to branch state and trigger downstream CI/deploys. |
| `gh extension *` | Any `gh extension` subcommand. `install` and `upgrade` pull remote code that then runs in-process under the operator's GitHub credentials on every subsequent `gh` invocation; `remove`/`list`/`search`/`exec` are blocked alongside to keep the namespace simple. Extensions belong to a deliberate operator decision, not an agent. |
| `gh gpg-key *` | Any `gh gpg-key` subcommand. `add` installs a persistent commit-signing identity an attacker could use to impersonate the operator on signed commits; `delete` can lock the operator out of signed-commit policies; `list` leaks the key-fingerprint inventory. Out-of-band key management only. |
| `gh issue transfer*` | Moves an issue (with its history and attachments) into a different repository. The destination repo can be attacker-controlled — equivalent to data exfiltration of the issue's contents. Issue transfers must be a deliberate human action. |
| `gh pr merge*` | CLI parallel to the `/pulls/*/merge` API deny. Merges are destructive to branch state and trigger downstream CI/deploys. |
| `gh repo delete*` | Permanently deletes a repository. No undo from the API; recovery requires GitHub support and is not guaranteed. |
| `gh secret *` | Any `gh secret` subcommand. `set`/`remove` mutate CI secrets under the operator's identity; `list` leaks secret names — exact same risk class as the `gh api * /actions/secrets*` deny ("Even GETs leak secret names"). Out-of-band secret management only. |
| `gh ssh-key *` | Any `gh ssh-key` subcommand. `add` is a persistent auth backdoor giving shell-equivalent push access until revoked; `delete` can lock the operator out; `list` leaks the key-fingerprint inventory. Out-of-band key management only. |
| `gh variable *` | Any `gh variable` subcommand. Mirror of the `gh secret *` rule for Actions variables. Variables are unencrypted secrets-lite; even `list` exposes their values directly, so the entire namespace is blocked and managed out-of-band. |
| `gh workflow disable*` | Disabling a workflow can silently turn off security-critical CI (CodeQL, security-review, lint gates). Must never be done autonomously. |
| `gh workflow enable*` | Re-enabling a workflow can silently restart paused CI (e.g. security scans deliberately disabled during incident response) without operator review. |
| `git branch -D*` | Force-deletes local branches regardless of merge status. Can destroy unmerged work with no recovery path. |
| `git clean*` | Any invocation of `git clean` is blocked. All useful variants (`-f`, `-fd`, `-xfd`) force-delete untracked files with no recovery path; the wildcard covers every flag order. Can silently wipe in-progress work the agent has not yet surfaced to the operator. |
| `git push --force*` | Rewrites remote history. Can permanently destroy other contributors' work. |
| `git reset --hard*` | Discards all uncommitted local changes without any recovery path. |
| `rm -rf*` | Recursive force-delete with no confirmation and no undo. Sandbox `allowWrite` does not protect here because `.` (the repo) is writable; `rm -rf .` would erase the working tree and `.git/`. |
| `sudo*` | Prevents privilege escalation attempts. The sandbox already blocks privileged operations, but denying `sudo` outright avoids accidental approval prompts and makes the intent explicit. |

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
