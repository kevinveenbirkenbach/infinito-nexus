# CLAUDE.md

## Startup — MUST DO at the Start of Every Conversation

You MUST read `AGENTS.md` and follow all instructions in it at the start of every conversation before doing anything else. Do NOT skip this, even for short or simple requests.

## Interaction Rules

- Questions MUST NOT lead to modifications, manipulation of files, code, or state.
- Only explicit commands MAY trigger modifications or manipulation.
- You MUST prefer commands that are already permitted in [.claude/settings.json](.claude/settings.json) over commands that require interactive approval. If an equivalent permitted command exists, you MUST use it instead of the restricted one.

## Code Execution

- You MUST always prefer `make` targets over running underlying scripts, `docker`, `docker compose`, `ansible-playbook`, `python`, or shell invocations directly, whenever an equivalent target exists in the [`Makefile`](Makefile). Inspect the `Makefile` first and only fall back to the raw command when no target covers the operation.
- When passing variables to `make`, you MUST pass them **after** the target as make-style arguments, NOT as a shell-env prefix before `make`. This keeps the command matchable by the `Bash(make*)` permission entry in [.claude/settings.json](.claude/settings.json) and avoids unnecessary approval prompts.
    - ✅ `make deploy-fresh-purged-apps APPS=web-app-nextcloud SERVICES_DISABLED="matomo"`
    - ❌ `SERVICES_DISABLED="matomo" APPS=web-app-nextcloud make deploy-fresh-purged-apps`
    - GNU Make automatically exports both command-line variables and inherited shell-env variables to recipe shells, so both forms are functionally equivalent. The make-suffix form is REQUIRED for agent use solely because of the `Bash(make*)` permission prefix match.
- You SHOULD run permitted commands (listed in [.claude/settings.json](.claude/settings.json)) directly on the host.
- For commands that are NOT permitted on the host, you MUST run them inside the application containers instead. Use `make up` (or the appropriate Make target) to start the stack, then use `make exec` to open a shell inside the container.
- The repository is mounted into the container at `/opt/src/infinito` (see [compose.yml](compose.yml)), so code changes are immediately available there.
- This avoids permission prompts and keeps the workflow uninterrupted.

## Configuration

- Project-level permissions and sandbox rules are defined in [.claude/settings.json](.claude/settings.json).
- See [code.claude.com](https://code.claude.com/docs/en/settings) for documentation on how to modify it.

## Documentation

See the [Claude Code documentation](https://code.claude.com/docs/en/overview) for further information. For human contributor guidance on working with agents, see [here](docs/contributing/tools/agents/common.md).
