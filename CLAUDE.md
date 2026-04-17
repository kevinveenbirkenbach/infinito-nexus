# CLAUDE.md

## Startup: MUST DO at the Start of Every Conversation 🚀

You MUST read `AGENTS.md` and follow all instructions in it at the start of every conversation before doing anything else.

## Permission State Announcement at Session Start 📢

At the start of every new conversation, after reading `AGENTS.md`, you MUST read [.claude/settings.json](.claude/settings.json) and output a concise summary of the current permission state to the operator. Do NOT hardcode the content of the summary from this document; derive it from the live settings file so the output stays accurate when the settings change.

The summary MUST cover, in this order:

1. Whether the sandbox is enabled (`sandbox.enabled`) and, if so, the concrete `allowWrite` and `denyRead` paths.
2. The list of pre-authorized commands (`permissions.allow` entries).
3. The list of commands that will prompt for approval (`permissions.ask` entries).
4. The list of unconditionally blocked commands (`permissions.deny` entries).

Present the summary once per session. Do not repeat it unless the operator explicitly asks. Do not propose the `/sandbox` command; if the sandbox config indicates it is already active, state that plainly.

## Interaction Rules 💬

- A question MUST NOT modify files, code, or state. Only explicit commands MAY.
- You MUST prefer commands permitted in [.claude/settings.json](.claude/settings.json) over commands that require interactive approval when an equivalent exists.

## Code Execution ⚙️

- You MUST prefer `make` targets over raw `docker`/`docker compose`/`ansible-playbook`/`python`/shell invocations whenever an equivalent target exists in the [`Makefile`](Makefile). Inspect the `Makefile` first; fall back to the raw command only when no target covers the operation. The reason is operational consistency, not permissioning — raw commands also auto-allow under the sandbox.
- You SHOULD run sandbox-confined commands directly on the host. The sandbox bounds what they can read, write, and reach — see [sandbox.md](docs/contributing/tools/agents/claude/sandbox.md).
- For commands that legitimately cannot run inside the sandbox (e.g. operations needing access to `~/.ssh` or `~/.gnupg`), use `make up` to start the stack and `make exec` to drop into a container shell. The repository is mounted at `/opt/src/infinito` (see [compose.yml](compose.yml)), so code changes are immediately available there.
- Commands listed under `permissions.ask` in [.claude/settings.json](.claude/settings.json) (e.g. `git commit`, `git push`, `curl`, `gh api`) still pause for explicit operator confirmation regardless of sandbox state.
- **Shell loops are FORBIDDEN. ⛔** You MUST NOT use `for`, `while`, `until`, or any other shell loop construct in any Bash tool call. Reason: shell control structures fall outside the sandbox auto-allow heuristic and trigger approval prompts even when every subcommand would individually auto-allow.
- **Multi-statement chains in shell invocations are FORBIDDEN. ⛔** You MUST NOT chain independent statements inside a single Bash tool call with **any** statement separator: `;`, a literal newline, `&&`, or `||`. Subshell groups `( cmd1; cmd2 )` and brace groups `{ cmd1; cmd2; }` are the same shape with different syntax and are equally forbidden. Reason: identical to the loop rule — the auto-allow heuristic evaluates the full line as a single compound and fails to match. Split the work across **separate Bash tool calls** (one statement per call) or use a single-command equivalent (`xargs`, `grep` with multiple args, a make target). The ban applies even when the right-hand side strictly requires the left.
- **File creation via shell heredoc is FORBIDDEN. ⛔** You MUST NOT use `cat > file <<EOF … EOF` or any variant (`tee > file <<EOF`, `printf "…" > file`, `echo "…" > file` for multi-line content) to create or overwrite files. Use the **Write tool**. For editing an existing file, use **Edit**, not `sed -i`/`awk -i`. Reason: Write/Edit land structured in the transcript and diff; heredoc + redirect shapes also fall out of the auto-allow heuristic and drop into ask.
- **For searching file contents, use the Grep tool.** If shelling out is unavoidable, use a single `grep` invocation with multiple file arguments (e.g. `grep -nE 'pattern' file1 file2 file3`) or a recursive call with a path/glob (e.g. `grep -rnE 'pattern' path/`).

## Configuration 🛠️

- Project-level permissions and sandbox rules are defined in [.claude/settings.json](.claude/settings.json).
- See [code.claude.com](https://code.claude.com/docs/en/settings) for documentation on how to modify it.

## Documentation 📝

See the [Claude Code documentation](https://code.claude.com/docs/en/overview) for further information. For human contributor guidance on working with agents, see [here](docs/contributing/tools/agents/common.md).
