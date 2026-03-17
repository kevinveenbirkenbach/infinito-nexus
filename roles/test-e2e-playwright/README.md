# Test: E2E Playwright Runner

## Description

This Ansible role provides a generic, reusable Playwright end-to-end (E2E) test runner
for the Infinito.Nexus ecosystem.

It automatically discovers roles that ship a Playwright test project under:

- `roles/<application_id>/templates/playwright.env.j2`
- `roles/<application_id>/files/playwright.spec.js`

A role is considered Playwright-enabled if it provides:

- `roles/<application_id>/templates/playwright.env.j2`

The role then stages the Playwright project to a local staging directory, renders a `.env`
file from `templates/playwright.env.j2`, optionally waits until the application is reachable, and executes
Playwright inside a pinned Docker image.

## Overview

This role:
- Discovers Playwright-enabled roles by scanning `roles/*/templates/playwright.env.j2`
- Supports allow-/deny-lists via `TEST_E2E_PLAYWRIGHT_ONLY_ROLES` and `TEST_E2E_PLAYWRIGHT_SKIP_ROLES`
- Stages each Playwright project into `TEST_E2E_PLAYWRIGHT_STAGE_BASE_DIR/<application_id>`
- Injects central default `package.json` and `playwright.config.js` when an app role omits them
- Copies role-specific `files/playwright.spec.js` into the staged `tests/playwright.spec.js`
- Renders `.env` from `templates/playwright.env.j2` using Ansible variables (`application_id`, `domains`, `users`, `applications`)
- Optionally waits until the application responds with HTTP `200` or `302`
- Injects CA trust automatically for `TLS_MODE=self_signed` (via `CA_TRUST.*`), so Playwright accepts self-signed cert chains
- Runs Playwright in Docker with stable browser settings (`--ipc=host`, `--shm-size=1g`)
- Stores per-role reports/artifacts under `TEST_E2E_PLAYWRIGHT_REPORTS_BASE_DIR/<application_id>`

## Purpose

The purpose of this role is to provide a central E2E test primitive that can be executed
at the end of a deployment (for example, as a post task), without hardcoding tests in the
runner itself.

Each application role stays responsible for its own Playwright tests and configuration.
This role only provides the execution framework.

## Role Contract (What application roles must provide)

A Playwright-enabled role must provide:

```
roles/<application_id>/
    templates/playwright.env.j2
    files/playwright.spec.js
```

`package.json` and `playwright.config.js` are provided centrally by this role from:
`roles/test-e2e-playwright/examples/tests/playwright/`.

### `playwright.env.j2`

`templates/playwright.env.j2` is rendered into `.env` and passed to the test container via `--env-file`.

Inside `playwright.env.j2` you can resolve the application domain via:

- `{{ lookup('domain',application_id) }}`
- Typical for Playwright tests: `APP_BASE_URL={{ lookup('tls', application_id, 'url.base') }}`

## Included Example Files

This role ships a ready-to-copy Playwright example under:

`roles/test-e2e-playwright/examples/tests/playwright/`

Included files:
- `env.j2`
- `package.json`
- `playwright.config.js`
- `scripts/record.sh`
- `tests/smoke.spec.js`
- `volume/.gitkeep`

These files are examples. `package.json` and `playwright.config.js` are also used
as central defaults for every app role.

## Variables

### Staging & Reports
- `TEST_E2E_PLAYWRIGHT_STAGE_BASE_DIR` (default: `/tmp/test-e2e-playwright`)
- `TEST_E2E_PLAYWRIGHT_REPORTS_BASE_DIR` (default: `/var/lib/infinito/logs/test-e2e-playwright`)

### Playwright runtime
- `TEST_E2E_PLAYWRIGHT_IMAGE` (default: `mcr.microsoft.com/playwright:v1.50.1-noble`)
- `TEST_E2E_PLAYWRIGHT_COMMAND` (default: `npm install --no-fund --no-audit && npx playwright test`)

### Readiness wait
- `TEST_E2E_PLAYWRIGHT_WAIT_ENABLED` (default: `true`)
- `TEST_E2E_PLAYWRIGHT_WAIT_RETRIES` (default: `30`)
- `TEST_E2E_PLAYWRIGHT_WAIT_DELAY` (default: `5`)

### Discovery filters
- `TEST_E2E_PLAYWRIGHT_ONLY_ROLES` (default: `allowed_applications`)
- `TEST_E2E_PLAYWRIGHT_SKIP_ROLES` (default: `[]`)

## Design Notes

- The runner is intentionally test-agnostic at runtime: it executes only tests provided by application roles.
- The bundled example scaffold is optional and not used automatically.
- `templates/playwright.env.j2` acts as the stable marker for discovery and as the source of environment configuration.
- Playwright is executed in Docker for reproducibility and consistent browser dependencies.
- In `TLS_MODE=self_signed`, the role requires `CA_TRUST.cert_host`, `CA_TRUST.wrapper_host`, and `CA_TRUST.trust_name` and fails early if cert/wrapper files are missing.

## How To Use The Example

1. Add the two app-specific files:
   - `roles/<application_id>/templates/playwright.env.j2`
   - `roles/<application_id>/files/playwright.spec.js`
2. Run deployment and include your app in `allowed_applications` (or leave it empty to run all discovered apps).
3. Keep `package.json` and `playwright.config.js` centralized in `roles/test-e2e-playwright/examples/tests/playwright/`.

Example override for running only one spec:

`-e TEST_E2E_PLAYWRIGHT_COMMAND='npm install --no-fund --no-audit && npx playwright test tests/smoke.spec.js'`

## Local Recording

The example scaffold includes `scripts/record.sh` for interactive local recording with
`playwright codegen`.

The script:
- prompts for the role name and target URL if they are not already set
- supports pre-seeding role and URL via `ROLE=...` and `URL=...`
- runs inside the official Playwright container image
- falls back across `container`, `docker`, and `podman`
- uses Firefox for local `codegen` by default because it is more stable than Chromium with forwarded Linux container GUIs
- disables the Playwright inspector window because it renders unreliably through container GUI forwarding
- writes generated code to `roles/<role>/files/playwright.spec.js` by default
- avoids distro-specific Playwright host dependencies

Examples:
- `make record-playwright`
- `ROLE=web-app-nextcloud URL=https://dashboard.infinito.example make record-playwright`
- `./scripts/record.sh https://dashboard.infinito.example`
- `./scripts/record.sh https://dashboard.infinito.example --browser chromium`
- `./scripts/record.sh https://dashboard.infinito.example --target javascript -o tests/login.spec.js`

Requirements:
- a local graphical Linux session (`DISPLAY` or `WAYLAND_DISPLAY`)
- one of `container`, `docker`, or `podman`
