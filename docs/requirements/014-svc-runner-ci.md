# 014 - Dedicated CI Runner via `svc-runner` Role

## User Story

As a developer, I want to run the Infinito.Nexus CI on a dedicated server so that the deploy + test cycle is no longer bound by local hardware restrictions.

## Idea

Add an `svc-runner` role that provisions a dedicated machine as an Infinito.Nexus CI runner, plus a CLI entry point under [cli/deploy/runner/](../../cli/deploy/runner/) that drives an Infinito.Nexus deploy against that runner from a developer workstation.

## Acceptance Criteria

### Role: `svc-runner`

- [ ] A new role [`roles/svc-runner/`](../../roles/svc-runner/) exists and follows the role-meta layout in [layout.md](../contributing/design/services/layout.md) (including `meta/services.yml` with a `lifecycle` key, `meta/schema.yml`, and `tasks/main.yml`).
- [ ] When applied to a host, `svc-runner` brings up an Infinito.Nexus-capable CI runner on that host (the runner is the execution environment in which subsequent Infinito.Nexus deploys and tests run).
- [ ] The role is compatible with — and exercised by — the CLI script described under **CLI: `cli/deploy/runner/`** below; deploying through that script against a fresh host MUST yield a working runner without manual post-steps.
- [ ] `make test` passes with the new role in place.

### CLI: `cli/deploy/runner/`

- [ ] A new CLI entry point lives at [`cli/deploy/runner/`](../../cli/deploy/runner/) and is wired into the `infinito` CLI tree the same way the existing [`cli/deploy/dedicated/`](../../cli/deploy/dedicated/) and [`cli/deploy/development/`](../../cli/deploy/development/) commands are.
- [ ] Argument parsing MUST use Python's standard-library `argparse` module, matching the convention used by [cli/deploy/dedicated/command.py](../../cli/deploy/dedicated/command.py). Hand-rolled `sys.argv` parsing or third-party CLI frameworks (`click`, `typer`, etc.) MUST NOT be introduced.
- [ ] The script accepts the following parameters:
  - `hostname` (**required**) — the target server that will host the runner.
  - `port` (**optional**, MAY be omitted) — SSH/connection port for the target host.
  - `roles` (**required**) — the set of roles to deploy onto the runner (accepts space- and comma-separated lists, matching the normalisation used by [cli/deploy/dedicated/command.py](../../cli/deploy/dedicated/command.py)).
  - `distribution` (**required**) — the target OS distribution of the runner (used to pick distro-specific tasks inside `svc-runner`).
  - `output stream file` (**optional**, with a documented default value) — file path the deploy's stdout/stderr stream is written to; the default MUST be a stable, documented path under `/tmp/`.
- [ ] Running the script against a clean host deploys `svc-runner` (plus any additional `roles` passed in) onto that host, and the runner is reachable / healthy at the end of the run.
- [ ] `--help` documents every parameter above, including the default value of the output stream file, in the same style as [cli/deploy/dedicated/command.py](../../cli/deploy/dedicated/command.py).

### Tests & Documentation

- [ ] A unit-level test covers the CLI parameter parsing (required vs. optional parameters, the output-stream-file default, and the `roles` normalisation).
- [ ] The role's `README.md` documents the runner's purpose, the CLI entry point, and how to invoke it end-to-end.
- [ ] This requirement is cross-linked from the implementing PR, and the implementing PR is cross-linked back here per [requirements.md](../contributing/requirements.md).
