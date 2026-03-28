[Back to CONTRIBUTING hub](../../../CONTRIBUTING.md)

# Pull Request Templates

You MUST pick the template that matches your change. The table below links the actual templates.

| Change type | Template |
|---|---|
| Server and `web-*` changes | [server.md](../../../.github/PULL_REQUEST_TEMPLATE/server.md) |
| Workstation and `desk-*` changes | [workstation.md](../../../.github/PULL_REQUEST_TEMPLATE/workstation.md) |
| Shared system changes such as `sys-*`, `svc-*`, `dev-*`, `drv-*`, `pkgmgr`, `update-*`, or `user-*` | [system.md](../../../.github/PULL_REQUEST_TEMPLATE/system.md) |
| CI/CD and workflow changes | [pipeline.md](../../../.github/PULL_REQUEST_TEMPLATE/pipeline.md) |
| Documentation-only changes limited to `.md` or `.rst` files outside `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and `docs/agents/*` | [documentation.md](../../../.github/PULL_REQUEST_TEMPLATE/documentation.md) |
| Agent-specific changes limited to `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, or `docs/agents/*` | [agents.md](../../../.github/PULL_REQUEST_TEMPLATE/agents.md) |

## Pull Request Workflow Scope

The PR workflow classifies changes by the files that were touched:

| Scope | Matching files | CI behavior |
|---|---|---|
| `agents` | Only `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, or `docs/agents/*` | Requires the `agent` branch prefix, skips `ci-orchestrator`, and finishes green through the lightweight scope gate. |
| `documentation` | Only `.md` or `.rst` files outside the agent paths | Requires the `documentation` branch prefix, skips `ci-orchestrator`, and finishes green through the lightweight scope gate. |
| `full` | Anything else, or a mix of agent, documentation, and non-documentation files | Requires the `feature` or `fix` branch prefix and runs the full `ci-orchestrator` pipeline. |

## Pull Request Checklist

Before you open a Pull Request, you MUST verify all of the following:

- CI in your fork is green.
- Your branch is up to date with `main`.
- Your change is small and focused.
- Your Pull Request explains the problem, the solution, and the test result.
- Relevant documentation is updated.
- The correct Pull Request template is used.
- The Pull Request is linked to the related work item in [project.infinito.nexus](https://project.infinito.nexus/) and back.
- Screenshots, logs, traces, or migration notes are attached when they help review the change.
