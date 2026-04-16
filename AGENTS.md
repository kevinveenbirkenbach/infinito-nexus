# Agent Instructions 🤖

## Priority and Scope 🎯

- [CONTRIBUTING.md](CONTRIBUTING.md) is the SPOT for general contributor workflow, coding standards, testing, and review. You MUST read it and recursively scan all files it references under `docs/contributing/`.
- This file extends `CONTRIBUTING.md` with agent-specific execution instructions. In case of conflict, the rules in this file take precedence because they are more specific to automated execution.
- You MUST recursively scan all files referenced under `docs/agents/` to collect the full agent-specific execution flow.

## Reloading Instructions 🔄

If agent instructions change during a conversation, the agent MAY not pick up the changes automatically. To force a reload, send the following command:

> "Re-read AGENTS.md and apply all updated instructions."

## Permission Model 🔐

The project defines a single, tool-independent permission policy in [`.claude/settings.json`](.claude/settings.json). Although the file lives under `.claude/`, its `permissions` section (`allow`, `ask`, `deny`) **together with** its `sandbox` section is the SPOT for what automated agents MAY do in this repository, regardless of the underlying agent (Claude Code, Codex, Gemini, or any other). The OS-level sandbox is the primary containment layer; the permission lists are the policy gate that runs on top of it.

Every agent MUST:

- Read [`.claude/settings.json`](.claude/settings.json) at the start of each conversation and treat both its `permissions` and `sandbox` objects as binding policy.
- Match commands against the patterns exactly as Claude Code does: the command-line prefix is compared literally, `*` is a wildcard, and `deny` overrides `allow`.
- Treat `deny` entries as unconditional blocks. Agents MUST NOT execute any command matching a `deny` pattern, even if their native tooling would otherwise permit it.
- Treat `ask` entries as requiring an explicit, per-invocation operator confirmation in the current conversation before executing. A prior confirmation in another conversation MUST NOT be reused.
- Treat `allow` entries as pre-authorized. For Bash specifically, `sandbox.autoAllowBashIfSandboxed: true` additionally pre-authorizes any Bash command that runs inside the sandbox and matches no `deny` or `ask` rule; agents whose runtime does not provide an equivalent OS-level sandbox MUST instead treat unmatched Bash commands as `ask`.
- Respect the `sandbox.filesystem` section: `allowWrite` bounds the write scope, and paths listed under `denyRead` MUST NOT be read.
- Respect the `sandbox.network` section: outbound network calls are bounded by `allowedDomains`, and the `allowAllUnixSockets` / `allowLocalBinding` flags govern local socket and bind access.
- Respect the `sandbox.allowUnsandboxedCommands: false` setting: agents MUST NOT attempt to run Bash commands outside the sandbox via per-call escape hatches (e.g. the `dangerouslyDisableSandbox` parameter).

Agents that cannot technically enforce these rules (e.g. because their native runtime does not consult `.claude/settings.json`) MUST still follow the policy procedurally: before running a command, check it against the rules above and stop for confirmation when required.

Changes to the permission policy MUST be made by editing [`.claude/settings.json`](.claude/settings.json) so that all agents share the same source of truth. The rationale for each entry is documented in [settings.md](docs/contributing/tools/agents/claude/settings.md); the sandbox layer that accompanies these permissions is documented in [sandbox.md](docs/contributing/tools/agents/claude/sandbox.md).

## Role-Specific Instructions 📂

Individual roles MAY contain an `AGENTS.md` file with role-specific agent instructions.

- Before modifying any file inside a role directory, you MUST check whether `roles/<role>/AGENTS.md` exists.
- If it exists, you MUST read it and follow all instructions in it before making any changes to that role.
- Role-level `AGENTS.md` files MAY contain file-specific sections with rules scoped to individual files within the role.

## Temporary Files 🗑️

Agents MUST write all transient files (downloaded logs, intermediate output, scratch artefacts) under `/tmp`, never inside the repository working tree. The sandbox grants write access to `/tmp` (see [.claude/settings.json](.claude/settings.json) `sandbox.filesystem.allowWrite`); no other location outside the repo is permitted for agent-generated temp data. This keeps the working tree clean, avoids accidental commits of throwaway data, and confines agent side-effects to a single, easily-purged path.

## Skills 🎓

At the start of every conversation, the agent MUST check whether agent skills are installed by verifying that `.agents/skills/` exists and is non-empty. If skills are missing, the agent MUST notify the user once with:

> Agent skills not installed. Run `make install-skills` to enable caveman and other agent skills.

The agent MUST NOT repeat this notice within the same conversation.

## For Humans 👥

Human contributors working alongside AI agents MUST read [here](docs/contributing/tools/agents/common.md).
