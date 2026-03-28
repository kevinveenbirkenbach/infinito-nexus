[Back to Development](README.md)

# CI Failures and Debugging

If CI fails, follow a clean debugging workflow:

1. Export the raw failing logs.
2. Save them locally as `job-logs.txt`.
3. Decide whether the failure belongs to your branch or to something unrelated.
4. Fix related failures in the same branch.
5. Open an issue for unrelated failures instead of mixing them into your branch.

Important:

- You MUST NOT debug from screenshots alone. Use raw logs.
- You MUST NOT commit log files to the repository.
- If a [Playwright](https://playwright.dev/) job fails, you MUST also download the Playwright assets, store them in `/tmp/`, and analyze them together with the logs.

You SHOULD use targeted manual CI jobs instead of rerunning the full pipeline if you only need one focused check.

Prefer the manual workflow in [entry-manual.yml](../../../.github/workflows/entry-manual.yml):

- Select your branch.
- Use `debian` unless you have a clear reason to use a different distro.
- Limit the run to the affected app when possible.

This gives faster feedback and protects shared CI runners.

More information [here](https://hub.infinito.nexus/t/infinito-nexus-ci-cd-debugging-guide/462).
