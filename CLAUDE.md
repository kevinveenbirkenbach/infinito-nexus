# CLAUDE.md

## Startup: MUST DO at the Start of Every Conversation 🚀

You MUST read `AGENTS.md` and follow all instructions in it at the start of every conversation before doing anything else. Do NOT skip this, even for short or simple requests.

## Permission State Announcement at Session Start 📢

At the start of every new conversation, after reading `AGENTS.md`, you MUST read [.claude/settings.json](.claude/settings.json) and output a concise summary of the current permission state to the operator. Do NOT hardcode the content of the summary from this document; derive it from the live settings file so the output stays accurate when the settings change.

The summary MUST cover, in this order:

1. Whether the sandbox is enabled (`sandbox.enabled`) and, if so, the concrete `allowWrite` and `denyRead` paths.
2. The list of pre-authorized commands (`permissions.allow` entries).
3. The list of commands that will prompt for approval (`permissions.ask` entries).
4. The list of unconditionally blocked commands (`permissions.deny` entries).

Present the summary once per session. Do not repeat it unless the operator explicitly asks. Do not propose the `/sandbox` command; if the sandbox config indicates it is already active, state that plainly.

## Interaction Rules 💬

- Questions MUST NOT lead to modifications, manipulation of files, code, or state.
- Only explicit commands MAY trigger modifications or manipulation.
- You MUST prefer commands that are already permitted in [.claude/settings.json](.claude/settings.json) over commands that require interactive approval. If an equivalent permitted command exists, you MUST use it instead of the restricted one.

## Code Execution ⚙️

- You MUST always prefer `make` targets over running underlying scripts, `docker`, `docker compose`, `ansible-playbook`, `python`, or shell invocations directly, whenever an equivalent target exists in the [`Makefile`](Makefile). Inspect the `Makefile` first and only fall back to the raw command when no target covers the operation. The reason is operational consistency, not permissioning: sandbox-confined Bash is auto-allowed via `sandbox.autoAllowBashIfSandboxed` (see [settings.md](docs/contributing/tools/agents/claude/settings.md)), so raw commands also execute without prompts.
- You SHOULD run sandbox-confined commands directly on the host. The sandbox bounds what they can read, write, and reach — see [sandbox.md](docs/contributing/tools/agents/claude/sandbox.md).
- For commands that legitimately cannot run inside the sandbox (e.g. operations needing access to `~/.ssh` or `~/.gnupg`), use `make up` to start the stack and `make exec` to drop into a container shell. The repository is mounted at `/opt/src/infinito` (see [compose.yml](compose.yml)), so code changes are immediately available there.
- Commands listed under `permissions.ask` in [.claude/settings.json](.claude/settings.json) (e.g. `git commit`, `git push`, `curl`, `gh api`) still pause for explicit operator confirmation regardless of sandbox state.
- You MUST prefer single-command forms over shell control structures when the task can be expressed either way. For scanning multiple files for patterns, use one `grep` invocation with multiple file arguments (e.g. `grep -nE 'pattern' file1 file2 file3`) or the built-in Grep tool — do NOT wrap per-file `grep` calls inside `for`/`while` loops. Avoid `for`/`while` loops, nested pipes, and multi-statement `;`/`&&` chains for operations that have a native single-command equivalent. Reason: shell control structures frequently fall outside the sandbox auto-allow heuristic and trigger unnecessary approval prompts, even when every subcommand would individually auto-allow.

## Configuration 🛠️

- Project-level permissions and sandbox rules are defined in [.claude/settings.json](.claude/settings.json).
- See [code.claude.com](https://code.claude.com/docs/en/settings) for documentation on how to modify it.

## Documentation 📝

See the [Claude Code documentation](https://code.claude.com/docs/en/overview) for further information. For human contributor guidance on working with agents, see [here](docs/contributing/tools/agents/common.md).
