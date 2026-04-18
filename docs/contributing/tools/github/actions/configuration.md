# CI Configuration ⚙️

This page is the SPOT (single point of truth) for every repository variable that controls GitHub Actions CI behaviour in this repo. For the workflow catalog see [workflows.md](workflows.md); for the CI flow see [pipeline.md](../../../artefact/git/pipeline.md).

Repository variables are set under **Settings → Secrets and variables → Actions → Variables**.

## Variables 📋

| Variable | Workflow | Default (unset) | Set to activate |
|---|---|---|---|
| `CI_CANCEL_IN_PROGRESS` | [entry-push-latest.yml](../../../../../.github/workflows/entry-push-latest.yml) | Cancels in-progress runs on new push | `false` to keep in-progress runs alive |
| `CI_RUN_ON_MAIN` | [entry-push-latest.yml](../../../../../.github/workflows/entry-push-latest.yml) | Pushes to `main` skip CI | `true` to run CI on `main` pushes too |

## `CI_CANCEL_IN_PROGRESS` 🛑

Controls whether a new push cancels an already-running CI pipeline on the same branch.

**Default behaviour (variable not set or set to any value other than `false`):**
In-progress runs are cancelled when a new push arrives. This is the recommended setting for most workflows.

**To disable cancellation:**

1. Open the repository on GitHub.
2. Go to **Settings → Secrets and variables → Actions**.
3. Switch to the **Variables** tab.
4. Click **New repository variable**.
5. Set **Name** to `CI_CANCEL_IN_PROGRESS` and **Value** to `false`.
6. Save.

**To re-enable cancellation:**

Delete the variable or change its value to anything other than `false` (e.g. `true`).

**How it works:**

```yaml
cancel-in-progress: ${{ vars.CI_CANCEL_IN_PROGRESS != 'false' }}
```

| Variable value | Expression result | Behaviour |
|---|---|---|
| *(not set / empty)* | `'' != 'false'` → `true` | Cancels in-progress runs ✓ |
| `false` | `'false' != 'false'` → `false` | Does **not** cancel ✓ |
| `true` | `'true' != 'false'` → `true` | Cancels in-progress runs ✓ |

## `CI_RUN_ON_MAIN` 🎯

Controls whether pushes to `main` trigger the CI pipeline. Pushes to all other branches covered by the workflow (`feature/**`, `hotfix/**`, `fix/**`, `alert-autofix-*`) are unaffected.

**Default behaviour (variable not set or set to any value other than `true`):**
Pushes to `main` are gated out at the `run-policy` job and CI is skipped.

**To enable CI on `main` pushes:**

1. Open the repository on GitHub.
2. Go to **Settings → Secrets and variables → Actions**.
3. Switch to the **Variables** tab.
4. Click **New repository variable**.
5. Set **Name** to `CI_RUN_ON_MAIN` and **Value** to `true`.
6. Save.

**To disable again:**

Delete the variable or change its value to anything other than `true`.

**How it works:**

The gate is applied inside [push_ci_policy.sh](../../../../../scripts/meta/resolve/push_ci_policy.sh), which the `run-policy` job invokes. When `GITHUB_REF == refs/heads/main` and `CI_RUN_ON_MAIN != 'true'`, the job emits `should_run=false` and every downstream job is skipped.

| Variable value | Ref is `main` | Behaviour |
|---|---|---|
| *(not set / empty)* | yes | CI skipped ✓ |
| `true` | yes | CI runs ✓ |
| any other value | yes | CI skipped ✓ |
| *(any)* | no | Unaffected (CI runs per branch rules) ✓ |
