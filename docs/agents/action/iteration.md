# Iteration

Use this page when you are iterating on a local app deploy during debugging or development.

## Loop

- Unless the user explicitly says to reuse the existing setup, you MUST start once with `APPS=<role> make deploy-fresh-purged-apps` to establish the baseline inventory and clean app state. Set `FULL_CYCLE=true` to also run the async update pass (pass 2).
- After that, you MUST use `APPS=<role> make deploy-reuse-kept-apps` for the default edit-fix-redeploy loop.
- Do NOT rerun `APPS=<role> make deploy-fresh-purged-apps` just because a deploy failed or you changed code. That restarts the stack unnecessarily and burns time.
- If the same failure still reproduces on the reuse path and you want to test whether app entity state is involved, use `APPS=<role> make deploy-reuse-purged-apps` once.
- After that targeted purge check, you MUST return to `APPS=<role> make deploy-reuse-kept-apps`.
- Only go back to `APPS=<role> make deploy-fresh-purged-apps` if you have concrete evidence that the inventory or host stack is broken, or you intentionally need a fresh single-app baseline again.
- If you need to validate the single-app init/deploy path separately, use `APPS=<role> make deploy-fresh-kept-apps`. It checks the clean single-app setup apart from the faster reuse path.

## Certificate Authority

- If the website uses locally deployed certificates, you MUST run `make trust-ca` before you inspect it in a browser. Otherwise the browser will warn about the local CA and the inspection will not be reliable.
- After `make trust-ca`, you MUST restart the browser so it picks up the updated trust store.

## Inspect

- Before you redeploy, you MUST complete all available inspections first. Check the live local output, local logs, and current browser state so the original state stays visible.
- To inspect files or run commands inside a running container, use `make exec`.
