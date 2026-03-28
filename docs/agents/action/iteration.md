[Back to AGENTS hub](../../../AGENTS.md)

# Iteration

Use this page when you are iterating on a local app deploy during debugging or development.

## Loop

- Start with `APP=<role> make deploy-fresh-purged-app`. This gives you a clean baseline by removing stale app data.
- Then use `APP=<role> make deploy-reuse-kept-app` for the normal fast loop. It reuses the existing inventory and keeps app data, so you can validate small changes quickly.
- If the same failure keeps reproducing on the reuse path, try `APP=<role> make deploy-reuse-purged-app` once as a targeted purge check. It keeps the inventory but clears the app entity so you can isolate state-related issues.
- After that targeted purge check, return to `APP=<role> make deploy-reuse-kept-app`.
- Only go back to `APP=<role> make deploy-fresh-purged-app` if the issue still reproduces after the reuse and targeted purge paths. That keeps full purges rare and only uses them when necessary.
- If you need to validate the single-app init/deploy path separately, continue with `APP=<role> make deploy-fresh-kept-app`. It checks the clean single-app setup apart from the faster reuse path.

## Certificate Authority

- If the website uses locally deployed certificates, run `make trust-ca` before you inspect it in a browser. Otherwise the browser will warn about the local CA and the inspection will not be reliable.
- After `make trust-ca`, restart the browser so it picks up the updated trust store.

## Inspect

- Before you redeploy, complete all available inspections first. Check the live local output, local logs, and current browser state so the original state stays visible.
