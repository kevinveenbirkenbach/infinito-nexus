# Claude Code 🤖

This folder documents the Claude Code agent configuration for this project. The authoritative policy lives in [`.claude/settings.json`](../../../../../.claude/settings.json); the pages here explain the reasoning behind each entry so future contributors understand *why* a rule exists before they change it.

## Pages 📄

| File | Purpose |
|---|---|
| [security.md](security.md) | Trust assumptions behind the Claude Code configuration: the two-layer containment model, what each assumption enables, and what happens if it is violated. Single source for the architectural reasoning. |
| [settings.md](settings.md) | The `allow`/`ask`/`deny` permission catalog, the `env` block (incl. the GPG signing override), and the rules for `.claude/settings.local.json`. |
| [sandbox.md](sandbox.md) | OS-level sandbox configuration: activation guarantees, fail-closed behavior, the no-unsandboxed-escape rule, Bash auto-allow, write scope, read restrictions, and network policy. |

For general agent workflow rules shared across all agents (Claude Code, Codex, Gemini, others), see [common.md](../common.md). For the Claude Code permission model reference, see [docs.anthropic.com](https://docs.anthropic.com/en/docs/claude-code/settings).
