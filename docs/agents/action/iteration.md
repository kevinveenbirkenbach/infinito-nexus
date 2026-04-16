# Iteration

Use this page when you are iterating on a local app deploy during debugging or development.

## Role Loop

- Before starting the loop, you MUST propose disabling all non-necessary services via `SERVICES_DISABLED` to reduce resource usage. In the typical case, this means keeping only the database and disabling everything else. Only proceed without this proposal if the user has already confirmed a full-stack setup.
- You MUST run `make test` before every deploy. Only proceed with the deploy if all tests pass.
- Unless the user explicitly says to reuse the existing setup, you MUST start once with `make deploy-fresh-purged-apps APPS=<roles>` to establish the baseline inventory and clean app state. Set `FULL_CYCLE=true` to also run the async update pass (pass 2).
- You MUST NOT run more than one deploy command at the same time. Deployments MUST be executed serially, never in parallel.
- To speed up debugging, you MAY pass multiple apps at once, e.g. `make deploy-fresh-purged-apps APPS="<roles> <roles>"`.
- After that, you MUST use `make deploy-reuse-kept-apps APPS=<roles>` for the default edit-fix-redeploy loop.
- Do NOT rerun `make deploy-fresh-purged-apps APPS=<roles>` just because a deploy failed or you changed code. That restarts the stack unnecessarily and burns time.
- If the same failure still reproduces on the reuse path and you want to test whether app entity state is involved, use `make deploy-reuse-purged-apps APPS=<roles>` once.
- After that targeted purge check, you MUST return to `make deploy-reuse-kept-apps APPS=<roles>`.
- Only go back to `make deploy-fresh-purged-apps APPS=<roles>` if you have concrete evidence that the inventory or host stack is broken, or you intentionally need a fresh single-app baseline again.
- Network or DNS failures during a local deploy count as concrete evidence that the host stack is broken. In that case, the next retry MUST be `make deploy-fresh-purged-apps APPS=<roles>` so the container stack is re-initialized.
- If you need to validate the single-app init/deploy path separately, use `make deploy-fresh-kept-apps APPS=<roles>`. It checks the clean single-app setup apart from the faster reuse path.

## Playwright Spec Loop

- After the first successful deploy has brought the app stack up, you MUST iterate role-local `files/playwright.spec.js` directly against the live running container instead of redeploying between every spec edit.
- For that inner loop you MUST use the [Playwright spec rerunner](../../../scripts/tests/e2e/rerun-spec.sh) (e.g. `scripts/tests/e2e/rerun-spec.sh <role>`, optionally followed by `--grep <pattern>` or other `npx playwright test` arguments). The script reuses the staging dir and rendered `.env` from the last deploy and reruns Playwright in the same container image the deploy-time runner uses.
- The staged Playwright project lives at `TEST_E2E_PLAYWRIGHT_STAGE_BASE_DIR/<application_id>` (default `/tmp/test-e2e-playwright/<application_id>`) with the rendered `.env` already in place. The script overwrites `tests/playwright.spec.js` from the repo before each run; you MUST NOT hand-edit the staged copy.
- You MUST keep iterating the spec in this inner loop until the test passes. Only spec-only changes belong in this loop.
- If the change touches anything **outside** `files/playwright.spec.js` (role tasks, templates, vars, config, `javascript.js`, `style.css`, or any other role asset that the deploy materializes), you MUST redeploy. Inner-loop spec runs do NOT pick up role changes.
- Prefer `make deploy-reuse-kept-apps APPS=<role>` for that redeploy. Fall back to `make deploy-fresh-purged-apps APPS=<role>` only when the reuse path has concrete evidence of broken inventory or host stack, per the rules in [Role Loop](#role-loop).
- You MUST still meet the live-application and logout-state requirements from [Agent `playwright.spec.js`](../files/role/playwright.spec.js.md) at the end of the inner loop.
- Once the spec passes in the inner loop, you MUST run one final pass through the [Role Loop](#role-loop) with `make deploy-fresh-purged-apps APPS=<role>` to confirm the spec still passes against a freshly provisioned stack, not only against the cached staging project.

## Workflow Loop

- When you are developing, optimizing, or debugging GitHub Actions workflows, you SHOULD explicitly propose `make act-workflow` as the default iterative local debug loop.
- You MUST NOT assume that Act should be used automatically for workflow work. If the user agrees with the proposal, you SHOULD use `make act-workflow` for the iteration loop.
- After the user agrees to use Act, you SHOULD rerun `make act-workflow` after each focused workflow change and inspect the new output before making further edits.
- If the workflow uses a distro matrix, you MUST iterate on one distro at a time instead of rerunning the whole matrix during the default debug loop.
- Debian SHOULD be the preferred distro for that focused workflow iteration unless the failure is clearly distro-specific or the user asked for a different distro.
- When you constrain an Act matrix run through `ACT_MATRIX`, you MUST use Act's `key:value` syntax instead of `key=value`. Otherwise Act may ignore the filter and rerun the whole matrix.
- For `.github/workflows/test-environment.yml`, the preferred focused Debian example is `make act-workflow ACT_WORKFLOW=.github/workflows/test-environment.yml ACT_JOB=test-environment ACT_MATRIX='dev_runtime_image:debian:bookworm'`.
- You SHOULD avoid jumping straight to repeated remote CI reruns when `make act-workflow` can validate the workflow locally and the user agreed to use it.
- You MAY widen the scope to `make act-app` or `make act-all` when the problem spans more than one workflow or `make act-workflow` is too narrow for the failure.

## Certificate Authority

- If the website uses locally deployed certificates, you MUST run `make trust-ca` before you inspect it in a browser. Otherwise the browser will warn about the local CA and the inspection will not be reliable.
- After `make trust-ca`, you MUST restart the browser so it picks up the updated trust store.
- If `make trust-ca` fails due to missing root permissions, you MUST use the alternative syntax `curl -k` (or `wget --no-check-certificate`) to skip certificate validation when checking URLs from the command line instead of fixing the trust store.

## Inspect

- Before you redeploy, you MUST complete all available inspections first. Check the live local output, local logs, and current browser state so the original state stays visible.
- To inspect files or run commands inside a running container, use `make exec`.
- When a local deploy fails, you SHOULD first inspect and, where practical, validate a fix inside the running container with `make exec` before starting another deploy. Use that live investigation to identify the concrete root cause and save iteration time.
- Once the root cause is understood, you MUST apply the real fix in the repository files and then continue the redeploy loop with the usual commands from this page. In-container fixes are only for diagnosis or short validation and MUST NOT replace the repo change.
