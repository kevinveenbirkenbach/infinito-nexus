[Back to AGENTS hub](../../AGENTS.md)

# Debugging

- Follow [CONTRIBUTING.md](../../CONTRIBUTING.md) for the general CI debugging workflow.

- Inspect relevant logs in `*job-logs.txt` or `*.log`.

## Playwright Failures

- If `*job-logs.txt` shows a Playwright failure, download the matching Playwright assets before you continue.
- Save the downloaded Playwright assets in `/tmp/` and keep them there.
- Output the storage path for the downloaded Playwright assets file.
- Analyze the downloaded Playwright assets together with `*job-logs.txt`.
