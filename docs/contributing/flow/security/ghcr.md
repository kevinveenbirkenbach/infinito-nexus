# GHCR Authentication Setup 🔐

This guide explains how to configure authentication for mirroring Docker images to GitHub Container Registry (GHCR) via GitHub Actions.

## Goal 🎯

GitHub Actions MUST be able to:

- Push images to `ghcr.io`
- Modify package visibility (e.g., set to public)
- Avoid authentication errors like `denied: denied`

## Required Configuration 🧩

### 1. Create a Personal Access Token (PAT)

Go to your [GitHub token settings](https://github.com/settings/tokens) and create a **classic token** with these scopes:

```
read:packages
write:packages
```

You MAY also add:

```
delete:packages
```

### 2. Store Credentials in the Repository or Organization

Go to `Settings → Secrets and variables → Actions`.

#### Secret: `GHCR_PAT`

- **Type:** Secret
- **Value:** The PAT created above
- **Visibility:** Public repositories (adjust as needed)

#### Variable: `GHCR_USERNAME`

- **Type:** Variable (not a secret — usernames are not sensitive)
- **Value:** The GitHub username that owns the PAT
- **Where:** Settings → Secrets and variables → Actions → **Variables** tab

Example:

```
kevinveenbirkenbach
```

You MUST NOT use the organization name, email address, or display name.
You MUST store this as a **variable**, not a secret. The workflow reads it via `vars.GHCR_USERNAME`.

## Fork Pull Requests 🚫

Secrets are NOT available in workflows triggered by `pull_request` events from forks — this is a GitHub security restriction. Workflows using `pull_request_target` DO receive secrets and MAY handle authentication for fork PRs.

## After Updating Secrets ♻️

Secrets are loaded at job start. After changing a secret you MUST either:

- Re-run the workflow manually, or
- Push a new commit to trigger a fresh run

## Mirror Visibility Update — Personal Accounts ⚠️

When the GHCR namespace belongs to a **personal account** (not an organization), the `GITHUB_TOKEN` issued by GitHub Actions is an installation token and MUST NOT be used to list or modify package visibility.
The `cli.mirror.publish` module will emit a GitHub Actions warning annotation and skip the visibility update if `GHCR_PAT` is not set.

To enable automatic visibility updates for personal accounts you MUST:

1. Create a **classic PAT** (see [Required Configuration](#required-configuration-) above) with at least `read:packages` and `write:packages` scopes.
2. Store it as the repository (or organization) secret `GHCR_PAT`.
3. Store the owning GitHub username as the variable `GHCR_USERNAME` (Settings → Actions → Variables).

The workflow automatically prefers `GHCR_PAT` over `GITHUB_TOKEN` when the secret is present.
If `GHCR_PAT` is absent, mirrored images are pushed successfully but their visibility is NOT automatically set to public.

## Troubleshooting 🧯

If login fails:

1. Verify `GHCR_PAT` is the current, valid token.
2. Ensure `GHCR_USERNAME` matches the account that created the token.
3. Re-run the workflow after any credential changes.
4. You MUST NOT use the organization name as the username.
5. If you see the warning *"GHCR visibility update skipped — GHCR_PAT required"* in the Actions log, `GHCR_PAT` is missing or not passed to the workflow — see [Mirror Visibility Update — Personal Accounts](#mirror-visibility-update--personal-accounts-) above.

## Best Practice ❤️

You SHOULD use a dedicated bot account (e.g., `infinito-nexus-bot`):

- Add it to the organization.
- Generate the PAT from that account.
- Store credentials as organization-level secrets/variables.
