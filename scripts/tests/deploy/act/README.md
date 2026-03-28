# Act Deploy Scripts

This is the SPOT for executable act deploy flows under `scripts/tests/deploy/act/`.

For local deploy flows, use [../local/README.md](../local/README.md).

## Entry Points

| Command | What it does | Notes |
|---|---|---|
| `make act-all` / `all.sh` | Runs `test-deploy-local.yml` across all selected distros. | Uses a linear matrix and passes the selected distro list through `DISTROS`. |
| `make act-app` / `app.sh` | Runs `test-deploy-local.yml` for one app. | Uses `whitelist` to limit the workflow to the selected app. |
| `make act-workflow` / `workflow.sh` | Runs any workflow file through `act`. | Supports custom job, matrix, container, network, and image settings. |
