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

#### Secret: `GHCR_USERNAME`

- **Type:** Secret
- **Value:** The GitHub username that owns the PAT

Example:

```
kevinveenbirkenbach
```

You MUST NOT use the organization name, email address, or display name.

## Fork Pull Requests 🚫

Secrets are NOT available in workflows triggered by `pull_request` events from forks — this is a GitHub security restriction. Workflows using `pull_request_target` DO receive secrets and MAY handle authentication for fork PRs.

## After Updating Secrets ♻️

Secrets are loaded at job start. After changing a secret you MUST either:

- Re-run the workflow manually, or
- Push a new commit to trigger a fresh run

## Troubleshooting 🧯

If login fails:

1. Verify `GHCR_PAT` is the current, valid token.
2. Ensure `GHCR_USERNAME` matches the account that created the token.
3. Re-run the workflow after any credential changes.
4. You MUST NOT use the organization name as the username.

## Best Practice ❤️

You SHOULD use a dedicated bot account (e.g., `infinito-nexus-bot`):

- Add it to the organization.
- Generate the PAT from that account.
- Store credentials as organization-level secrets/variables.
