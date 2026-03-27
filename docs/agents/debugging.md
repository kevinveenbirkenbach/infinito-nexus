[Back to AGENTS hub](../../AGENTS.md)

# Debugging

Use the failure source to decide how to debug:

- If the failure happened during a local deploy, debug from the live local output and local logs.
- If the failure comes from GitHub, follow [CONTRIBUTING.md](../../CONTRIBUTING.md) and work from the downloaded `*job-logs.txt` or `*.log` files.
- If a run is still progressing and the user has not asked you to change course, wait for the long-running run to finish instead of interrupting it.

## Local Deploy Failures

- Before you redeploy, complete all available inspections first. Check the live local output, local logs, and current browser state so the original failure stays visible.
- If the website uses locally deployed certificates, run `make trust-ca` before you inspect it in a browser. Otherwise the browser will warn about the local CA and the inspection will not be reliable.
- After `make trust-ca`, restart the browser so it picks up the updated trust store.
- On the first local deploy failure, rerun the affected app with `APP=<role> make deploy-fresh-purged-app`. For alarm failures, use this retry path because it rebuilds the full `servers.yml` inventory in the dedicated shape.
- If you need to validate the single-app `servers.yml` path after that, continue with `APP=<role> make deploy-fresh-kept-app`.
- Use `APP=<role> make deploy-reuse-kept-app` only when you intentionally work from the `${TEST_DEPLOY_TYPE}.yml` inventory flow created by `make container-irefresh-inventory` or `make deploy-fresh-kept-all`.
- Keep iterating locally until the issue is fixed, unless the user explicitly asks you to switch context.

## GitHub / CI Logs

- Inspect relevant logs in `*job-logs.txt` or `*.log`.
- Treat the downloaded GitHub logs as the source of truth for CI failures.

### Playwright Failures

- If `*job-logs.txt` shows a Playwright failure, download the matching Playwright assets before you continue.
- Save the downloaded Playwright assets in `/tmp/` and keep them there.
- Output the storage path for the downloaded Playwright assets file.
- Analyze the downloaded Playwright assets together with `*job-logs.txt`.
