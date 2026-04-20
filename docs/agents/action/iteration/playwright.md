# Playwright Spec Loop

This page defines the inner loop for iterating on a role-local `files/playwright.spec.js` against an already-running app stack, without redeploying between edits.

## Definitions

- **Inner loop**: the edit-rerun cycle on `roles/<role>/files/playwright.spec.js` driven by `scripts/tests/e2e/rerun-spec.sh`, without a redeploy.
- **Staging dir**: `TEST_E2E_PLAYWRIGHT_STAGE_BASE_DIR/<role>` (default `/tmp/test-e2e-playwright/<role>`). Contains the rendered `.env` and the Playwright project from the last deploy.
- **Baseline deploy**: a successful `make deploy-fresh-purged-apps APPS=<role> FULL_CYCLE=true` run as defined in [Role Loop](role.md).
- **Pass**: `scripts/tests/e2e/rerun-spec.sh <role>` exits `0` AND every MUST in [Contributing `playwright.spec.js`](../../../contributing/artefact/files/role/playwright.specs.js.md) holds for the resulting run.

## Preconditions

You MUST NOT enter the inner loop unless all of the following hold:

1. A baseline deploy for `<role>` completed successfully in the current environment.
2. The app stack for `<role>` is still running.
3. The staging dir exists and contains a non-empty `.env`.
4. `roles/<role>/files/playwright.spec.js` exists.

If any precondition fails, you MUST return to [Role Loop](role.md) and re-establish the baseline before continuing.

## Required reading

You MUST load the following pages before editing any file, in this order:

1. [Contributing `playwright.spec.js`](../../../contributing/artefact/files/role/playwright.specs.js.md): authoritative MUSTs for the spec content. Every MUST there is an acceptance criterion for this loop.
2. [Agent `playwright.spec.js` procedure](../../files/role/playwright.spec.js.md): how to generate or update the spec.
3. [Agent `playwright.env.j2` procedure](../../files/role/playwright.env.j2.md): rendered test input contract; required whenever the spec reads a new variable.
4. [Playwright Tests](../../../contributing/actions/testing/playwright.md): framework SPOT for runner, image pin, and recording tools.
5. [Role Loop](role.md): baseline deploy, Certificate Authority trust, Inspect-before-redeploy.

## Procedure

1. Verify every item in [Preconditions](#preconditions). If any fails, exit this page and follow [Role Loop](role.md).
2. Edit `roles/<role>/files/playwright.spec.js`. You MUST NOT hand-edit the staged copy under `TEST_E2E_PLAYWRIGHT_STAGE_BASE_DIR/<role>/tests/`; the rerunner overwrites it from the repo on each run.
3. Run `scripts/tests/e2e/rerun-spec.sh <role>`. You MAY append `--grep <pattern>` or any other `npx playwright test` argument. The script reuses the staging dir, the rendered `.env`, and the same container image the deploy-time runner uses.
4. If the script exits `0`, go to [Exit](#exit).
5. If the script exits non-zero:
   1. If the failure is caused by a change needed **outside** `files/playwright.spec.js` (role tasks, templates, vars, config, `javascript.js`, `style.css`, or any other role asset the deploy materializes), go to [Escape](#escape).
   2. Otherwise, adjust the spec and return to step 2.

## Exit

You MUST NOT report the task complete until all of the following hold:

1. `scripts/tests/e2e/rerun-spec.sh <role>` has exited `0` on the current spec.
2. Every MUST in [Contributing `playwright.spec.js`](../../../contributing/artefact/files/role/playwright.specs.js.md) holds, including the live-application assertion and the logged-out final state.
3. A final `make deploy-fresh-purged-apps APPS=<role> FULL_CYCLE=true` run has completed with the spec passing against the freshly provisioned stack. Inner-loop passes alone do NOT satisfy this gate.

## Escape

When the failure requires a change outside `files/playwright.spec.js`:

1. You MUST stop the inner loop. Inner-loop runs do NOT pick up role changes.
2. You SHOULD run `make deploy-reuse-kept-apps APPS=<role>` for the redeploy.
3. You MUST NOT fall back to `make deploy-fresh-purged-apps APPS=<role> FULL_CYCLE=true` unless the reuse path has concrete evidence of a broken inventory or host stack, per [Role Loop](role.md).
4. After the redeploy succeeds, return to [Procedure](#procedure) step 1.
