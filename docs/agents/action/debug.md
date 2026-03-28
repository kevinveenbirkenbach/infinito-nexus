[Back to AGENTS hub](../../../AGENTS.md)

# Debugging

Use the failure source to decide how to debug:

- If the failure happened during a local deploy, you MUST debug from the live local output and local logs.
- If the failure comes from GitHub, you MUST follow [CONTRIBUTING.md](../../../CONTRIBUTING.md) and work from the downloaded `*job-logs.txt` or `*.log` files.
- If a run is still progressing and the user has not asked you to change course, you MUST wait for the long-running run to finish instead of interrupting it.

## Local Deploy Failures

### Retry Loop

- For the shared local retry loop, you MUST follow [Iteration](iteration.md).

## GitHub / CI Logs

- You MUST inspect relevant logs in `*job-logs.txt` or `*.log`.
- You MUST treat the downloaded GitHub logs as the source of truth for CI failures.

### Playwright Failures

- If `*job-logs.txt` shows a Playwright failure, you MUST download the matching Playwright assets before you continue.
- You MUST save the downloaded Playwright assets in `/tmp/` and keep them there.
- You MUST output the storage path for the downloaded Playwright assets file.
- You MUST analyze the downloaded Playwright assets together with `*job-logs.txt`.
