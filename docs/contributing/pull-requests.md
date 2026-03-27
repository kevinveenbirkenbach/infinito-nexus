[Back to CONTRIBUTING hub](../../CONTRIBUTING.md)

# Pull Request Templates

Pick the template that matches your change. The table below links the actual templates.

| Change type | Template |
|---|---|
| Server and `web-*` changes | [server.md](../../.github/PULL_REQUEST_TEMPLATE/server.md) |
| Workstation and `desk-*` changes | [workstation.md](../../.github/PULL_REQUEST_TEMPLATE/workstation.md) |
| Shared system changes such as `sys-*`, `svc-*`, `dev-*`, `drv-*`, `pkgmgr`, `update-*`, or `user-*` | [system.md](../../.github/PULL_REQUEST_TEMPLATE/system.md) |
| CI/CD and workflow changes | [pipeline.md](../../.github/PULL_REQUEST_TEMPLATE/pipeline.md) |
| Documentation-only changes | [documentation.md](../../.github/PULL_REQUEST_TEMPLATE/documentation.md) |
| Agent-specific changes | [agents.md](../../.github/PULL_REQUEST_TEMPLATE/agents.md) |

## Pull Request Checklist

Before you open a Pull Request, make sure:

- CI in your fork is green.
- Your branch is up to date with `main`.
- Your change is small and focused.
- Your Pull Request explains the problem, the solution, and the test result.
- Relevant documentation is updated.
- The correct Pull Request template is used.
- The Pull Request is linked to the related work item in [project.infinito.nexus](https://project.infinito.nexus/) and back.
- Screenshots, logs, traces, or migration notes are attached when they help review the change.
