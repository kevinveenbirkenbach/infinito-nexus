# Agent Instructions

## Priority and Scope

- [CONTRIBUTING.md](CONTRIBUTING.md) is the SPOT for general contributor workflow, coding standards, testing, and review. You MUST read it and recursively scan all files it references under `docs/contributing/`.
- This file extends `CONTRIBUTING.md` with agent-specific execution instructions. In case of conflict, the rules in this file take precedence because they are more specific to automated execution.
- You MUST recursively scan all files referenced under `docs/agents/` to collect the full agent-specific execution flow.

## Reloading Instructions

If agent instructions change during a conversation, the agent MAY not pick up the changes automatically. To force a reload, send the following command:

> "Re-read AGENTS.md and apply all updated instructions."

## Role-Specific Instructions

Individual roles MAY contain an `AGENTS.md` file with role-specific agent instructions.

- Before modifying any file inside a role directory, you MUST check whether `roles/<role>/AGENTS.md` exists.
- If it exists, you MUST read it and follow all instructions in it before making any changes to that role.
- Role-level `AGENTS.md` files MAY contain file-specific sections with rules scoped to individual files within the role.

## Skills

At the start of every conversation, the agent MUST check whether agent skills are installed by verifying that `.agents/skills/` exists and is non-empty. If skills are missing, the agent MUST notify the user once with:

> Agent skills not installed. Run `make install-skills` to enable caveman and other agent skills.

The agent MUST NOT repeat this notice within the same conversation.

## For Humans

Human contributors working alongside AI agents MUST read [here](docs/contributing/tools/agents/common.md).
