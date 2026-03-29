# Branch

## CI Impact

The branch prefix MUST match the type of change. The [PR workflow](pull-request.md) uses it to classify the scope and decide which CI pipeline to run.

| Branch prefix | Scope | Matching files | CI behavior |
|---|---|---|---|
| `agent` | Changes to agent instructions or prompts | `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `docs/agents/*` | Skips [ci-orchestrator](../../../.github/workflows/ci-orchestrator.yml), finishes green through the lightweight scope gate. |
| `documentation` | Documentation-only changes | `**/*.md`, `**/*.rst` (outside agent paths) | Skips [ci-orchestrator](../../../.github/workflows/ci-orchestrator.yml), finishes green through the lightweight scope gate. |
| `feature` | New features or enhancements | `*` | Runs the full [ci-orchestrator](../../../.github/workflows/ci-orchestrator.yml) pipeline. |
| `fix` | Bug fixes | `*` | Runs the full [ci-orchestrator](../../../.github/workflows/ci-orchestrator.yml) pipeline. |

## Naming Conventions

The description MUST use `kebab-case` (lowercase words separated by hyphens) and SHOULD be short enough to read at a glance. 

The full branch name MUST follow one of the patterns below, depending on whether the change targets a specific role or is general:

| Case | Pattern | Example |
|---|---|---|
| General feature | `feature/<topic>` | `feature/ldap-integration` |
| Role feature | `feature/<role>/<topic>` | `feature/web-app-matomo/ldap-integration` |
| General fix | `fix/<topic>/<ticket-id>` | `fix/dns-resolution/taiga-123` |
| Role fix | `fix/<role>/<topic>/<ticket-id>` | `fix/web-app-matomo/login-redirect/taiga-789` |
| Documentation | `documentation/<topic>` | `documentation/contributing-setup` |
| Agent | `agent/<topic>` | `agent/improve-commit-instructions` |

`feature`, `documentation`, and `agent` branches MUST NOT reference a ticket ID.
