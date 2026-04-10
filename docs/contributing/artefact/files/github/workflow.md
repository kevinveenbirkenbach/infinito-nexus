# GitHub workflow files 🔄

This page is the SPOT for repository rules that govern GitHub Actions workflow files under `.github/workflows/`.
For the script placement rule that applies to extracted shell helpers, see [scripst.md](../../scripst.md).

## Shell execution 📜

- Multi-line shell logic in workflow `run:` blocks MUST be extracted into dedicated `.sh` files under `scripts/`.
- Workflow files MUST call those extracted `.sh` entry points instead of embedding longer shell programs inline.
- Short single-command invocations MAY stay inline when they do not contain meaningful control flow.
- Inline shell in workflow files SHOULD stay limited to small command calls, environment wiring, or direct script invocation.

## Separation of concerns 🧩

- GitHub workflow YAML MUST describe orchestration, permissions, triggers, inputs, and step order.
- Reusable shell behavior MUST live in script files, not in repeated workflow `run:` blocks.
- Non-shell helper logic MUST NOT be embedded as ad-hoc shell blobs inside workflow files.
