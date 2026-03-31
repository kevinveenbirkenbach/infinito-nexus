# Iteration

Use this page when you are iterating on a local app deploy during debugging or development.

## Loop

- Unless the user explicitly says to reuse the existing setup, you MUST start once with `APPS=<roles> make deploy-fresh-purged-apps` to establish the baseline inventory and clean app state. Set `FULL_CYCLE=true` to also run the async update pass (pass 2).
- To speed up debugging, you MAY pass multiple apps at once, e.g. `APPS="<roles> <roles>" make deploy-fresh-purged-apps`.
- After that, you MUST use `APPS=<roles> make deploy-reuse-kept-apps` for the default edit-fix-redeploy loop.
- Do NOT rerun `APPS=<roles> make deploy-fresh-purged-apps` just because a deploy failed or you changed code. That restarts the stack unnecessarily and burns time.
- If the same failure still reproduces on the reuse path and you want to test whether app entity state is involved, use `APPS=<roles> make deploy-reuse-purged-apps` once.
- After that targeted purge check, you MUST return to `APPS=<roles> make deploy-reuse-kept-apps`.
- Only go back to `APPS=<roles> make deploy-fresh-purged-apps` if you have concrete evidence that the inventory or host stack is broken, or you intentionally need a fresh single-app baseline again.
- If you need to validate the single-app init/deploy path separately, use `APPS=<roles> make deploy-fresh-kept-apps`. It checks the clean single-app setup apart from the faster reuse path.

## Workflow Loop

- When you are developing, optimizing, or debugging GitHub Actions workflows, you SHOULD explicitly propose `make act-workflow` as the default iterative local debug loop.
- You MUST NOT assume that Act should be used automatically for workflow work. If the user agrees with the proposal, you SHOULD use `make act-workflow` for the iteration loop.
- After the user agrees to use Act, you SHOULD rerun `make act-workflow` after each focused workflow change and inspect the new output before making further edits.
- If the workflow uses a distro matrix, you MUST iterate on one distro at a time instead of rerunning the whole matrix during the default debug loop.
- Debian SHOULD be the preferred distro for that focused workflow iteration unless the failure is clearly distro-specific or the user asked for a different distro.
- When you constrain an Act matrix run through `ACT_MATRIX`, you MUST use Act's `key:value` syntax instead of `key=value`. Otherwise Act may ignore the filter and rerun the whole matrix.
- For `.github/workflows/test-environment.yml`, the preferred focused Debian example is `ACT_WORKFLOW=.github/workflows/test-environment.yml ACT_JOB=test-environment ACT_MATRIX='dev_runtime_image:debian:bookworm' make act-workflow`.
- You SHOULD avoid jumping straight to repeated remote CI reruns when `make act-workflow` can validate the workflow locally and the user agreed to use it.
- You MAY widen the scope to `make act-app` or `make act-all` when the problem spans more than one workflow or `make act-workflow` is too narrow for the failure.

## Certificate Authority

- If the website uses locally deployed certificates, you MUST run `make trust-ca` before you inspect it in a browser. Otherwise the browser will warn about the local CA and the inspection will not be reliable.
- After `make trust-ca`, you MUST restart the browser so it picks up the updated trust store.
- If `make trust-ca` fails due to missing root permissions, you MUST use the alternative syntax `curl -k` (or `wget --no-check-certificate`) to skip certificate validation when checking URLs from the command line instead of fixing the trust store.

## Inspect

- Before you redeploy, you MUST complete all available inspections first. Check the live local output, local logs, and current browser state so the original state stays visible.
- To inspect files or run commands inside a running container, use `make exec`.
