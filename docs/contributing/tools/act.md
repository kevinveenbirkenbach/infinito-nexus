[Back to Tools](README.md)

# Act Workflow Checks

Use these commands from the repository root. They are thin wrappers around the local [act](https://nektosact.com/usage/) deployment scripts.

## Commands

| Category | Command | What it does | When to use it |
|---|---|---|---|
| All act checks | `make act-all` | Runs all act-based deploy checks. | Use this when you want the full local `act` validation set. |
| App act check | `make act-app` | Runs the act-based app deploy check. | Use this when you only need to validate the app deploy path. |
| Workflow act check | `make act-workflow` | Runs the act-based workflow deploy check. | Use this when you want to validate the workflow deploy path specifically. |

## Notes

- These commands are intended for local validation of the deploy workflows.
- The underlying scripts live in `scripts/tests/deploy/act/`.
- For broader test and validation guidance, see [Testing and Validation](../development/testing.md).
