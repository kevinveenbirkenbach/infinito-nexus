[Back to AGENTS hub](../../AGENTS.md)

# Development

## New Apps

- Use [CONTRIBUTING.md](../../CONTRIBUTING.md) as the SPOT for the general development workflow, testing, review, and coding standards.
- Treat the matching Pull Request template described in [Pull Requests](../../docs/contributing/pull-requests.md) and stored in [PULL_REQUEST_TEMPLATE](../../.github/PULL_REQUEST_TEMPLATE) as the SPOT for requirements, file checks, validation expectations, and the Definition of Done.
- Start from the smallest app-specific change that can be validated locally, then expand only when the requirements or behavior demand it.
- Keep the implementation, local validation, and PR template in sync so the app can be reviewed without guessing the intent.

## Bugs and Warnings

- Treat warnings about the concrete implementation, wiring, or runtime behavior as bugs that should be fixed.
- Do not leave implementation warnings unresolved just because they are inconvenient.
- If a warning points to an intentional exception, make the exception explicit and keep the follow-up visible.

## Debugging

- When a development run fails, switch to [Debugging](debugging.md) and follow the local-deploy or GitHub-log path that matches the failure source.
- Keep long-running runs alive and wait for them to finish unless the user explicitly asks you to steer away from them.

## Review Focus

- Ask whether the new app behaves correctly end to end, not just whether it compiles or deploys.
- Prefer fixing the real app bug over adding a comment that explains it away.
- Treat temporary warnings as a signal to remove the underlying problem later, not as a reason to normalize the exception.
