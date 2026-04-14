# CLAUDE.md

## Startup — MUST DO at the Start of Every Conversation

You MUST read `AGENTS.md` and follow all instructions in it at the start of every conversation before doing anything else. Do NOT skip this, even for short or simple requests.

## Interaction Rules

- Questions MUST NOT lead to modifications, manipulation of files, code, or state.
- Only explicit commands MAY trigger modifications or manipulation.
- You MUST prefer commands that are already permitted in [.claude/settings.json](.claude/settings.json) over commands that require interactive approval. If an equivalent permitted command exists, you MUST use it instead of the restricted one.

## Code Execution

- You SHOULD run permitted commands (listed in [.claude/settings.json](.claude/settings.json)) directly on the host.
- For commands that are NOT permitted on the host, you MUST run them inside the application containers instead. Use `make up` (or the appropriate Make target) to start the stack, then use `make exec` to open a shell inside the container.
- The repository is mounted into the container at `/opt/src/infinito` (see [compose.yml](compose.yml)), so code changes are immediately available there.
- This avoids permission prompts and keeps the workflow uninterrupted.

## Configuration

- Project-level permissions and sandbox rules are defined in [.claude/settings.json](.claude/settings.json).
- See [code.claude.com](https://code.claude.com/docs/en/settings) for documentation on how to modify it.

## Documentation

See the [Claude Code documentation](https://code.claude.com/docs/en/overview) for further information. For human contributor guidance on working with agents, see [here](docs/contributing/tools/agents/common.md).
