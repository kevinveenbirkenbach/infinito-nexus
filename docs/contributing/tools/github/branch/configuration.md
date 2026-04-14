# CI Configuration ⚙️

This page documents the repository variables that control CI pipeline behaviour.
Repository variables are set under **Settings → Secrets and variables → Actions → Variables**.

## `CI_CANCEL_IN_PROGRESS`

Controls whether a new push cancels an already-running CI pipeline on the same branch
in [entry-push-latest.yml](../../../../../.github/workflows/entry-push-latest.yml).

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
