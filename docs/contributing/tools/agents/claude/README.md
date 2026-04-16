# Claude Code 🤖

This folder documents the Claude Code agent configuration for this project. The authoritative policy lives in [`.claude/settings.json`](../../../../../.claude/settings.json); the pages here explain the reasoning behind each entry so future contributors understand *why* a rule exists before they change it.

## Pages 📄

| File | Purpose |
|---|---|
| [settings.md](settings.md) | Every permission entry (`allow`, `ask`, `deny`) in `.claude/settings.json`, with context on when it applies, why it is granted at that level, and its security implications. |
| [sandbox.md](sandbox.md) | OS-level sandbox configuration: activation guarantees, fail-closed behavior when the backend is missing, write scope, and read restrictions. |

For general agent workflow rules shared across all agents (Claude Code, Codex, Gemini, others), see [common.md](../common.md). For the Claude Code permission model reference, see [docs.anthropic.com](https://docs.anthropic.com/en/docs/claude-code/settings).
