[Back to AGENTS hub](../../../AGENTS.md)

# Iteration

Use this page when you are iterating on a local app deploy during debugging or development.

## Loop

- Start once with `APP=<role> make deploy-fresh-purged-app` to establish the baseline inventory and clean app state.
- After that, use `APP=<role> make deploy-reuse-kept-app` for the default edit-fix-redeploy loop.
- Do not rerun `APP=<role> make deploy-fresh-purged-app` just because a deploy failed or you changed code. That restarts the stack unnecessarily and burns time.
- If the same failure still reproduces on the reuse path and you want to test whether app entity state is involved, use `APP=<role> make deploy-reuse-purged-app` once.
- After that targeted purge check, return to `APP=<role> make deploy-reuse-kept-app`.
- Only go back to `APP=<role> make deploy-fresh-purged-app` if you have concrete evidence that the inventory or host stack is broken, or you intentionally need a fresh single-app baseline again.
- If you need to validate the single-app init/deploy path separately, use `APP=<role> make deploy-fresh-kept-app`. It checks the clean single-app setup apart from the faster reuse path.

## Certificate Authority

- If the website uses locally deployed certificates, run `make trust-ca` before you inspect it in a browser. Otherwise the browser will warn about the local CA and the inspection will not be reliable.
- After `make trust-ca`, restart the browser so it picks up the updated trust store.

## Inspect

- Before you redeploy, complete all available inspections first. Check the live local output, local logs, and current browser state so the original state stays visible.
