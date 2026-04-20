# Playwright Tests 🎭

This page is the SPOT for Playwright end-to-end test requirements, runner integration, and file contracts.
For implementation guidance when writing or updating role-local files, see
[Agent `playwright.spec.js`](../../../agents/files/role/playwright.spec.js.md) and
[Agent `playwright.env.j2`](../../../agents/files/role/playwright.env.j2.md).
For what the `files/playwright.spec.js` of a role MUST contain, see
[`playwright.spec.js` (role file rules)](../../artefact/files/role/playwright.specs.js.md).

## Framework 🧰

- [Playwright](https://playwright.dev/) runs inside Docker via the shared `test-e2e-playwright` role.
- There is no standalone `make` target for Playwright. Tests run as part of local deploy flows
  (e.g. `make deploy-fresh-purged-apps APPS=web-app-matomo FULL_CYCLE=true`). For spec-only
  iteration after the first successful deploy, see [Playwright Spec Loop](../../../agents/action/iteration/playwright.md).

## When to Write ✍️

- You MUST provide Playwright tests for every `web-*` role.
- For when a spec MUST be added or updated (including the `javascript.js` / `style.css` trigger), see the Scenarios section of [`playwright.spec.js`](../../artefact/files/role/playwright.specs.js.md#scenarios-).

## Role-Local Files 📁

Every Playwright-enabled role MUST provide exactly these two files:

| File | Purpose |
|---|---|
| `files/playwright.spec.js` | Test scenarios executed by the Playwright runner |
| `templates/playwright.env.j2` | Rendered `.env` passed to the Playwright container |

`playwright.config.js` MUST remain centralized in `roles/test-e2e-playwright/files/` and `package.json` in `roles/test-e2e-playwright/templates/package.json.j2` (rendered per-deploy into the staging dir). You MUST NOT duplicate or override either per role.

The `@playwright/test` version pinned into the rendered `package.json` comes from `images.playwright.version` in `roles/test-e2e-playwright/defaults/main.yml` via the `image_version` filter. That YAML value is the single source of truth for the Playwright version.

## CI Image Source 🪞

The Playwright container image is declared in `roles/test-e2e-playwright/defaults/main.yml` under `images.playwright` (`image:` + `version:`). CI mirrors that image into GHCR through the standard mirror pipeline before deploy tests run, so Playwright jobs do not depend on direct pulls from MCR during the test phase.

The `version:` MUST stay pinned to an exact Playwright version and distro pair such as `v1.59.1-noble`. You MUST NOT switch this to a mutable tag such as `latest`, because mutable upstream tags are more vulnerable to CDN propagation delays and make flaky CI failures much harder to reason about.

## Runner 🚀

The `test-e2e-playwright` role discovers Playwright-enabled roles through the presence of
`templates/playwright.env.j2`. For each discovered role it:

1. stages the test project
2. renders `.env` from `playwright.env.j2`
3. copies `files/playwright.spec.js` into the project as `tests/playwright.spec.js`
4. renders the central `templates/package.json.j2` and copies the central `files/playwright.config.js` into the staging dir
5. waits until the app is reachable
6. runs Playwright in Docker

## File Requirements 📄

See the dedicated SPOT pages for authoring rules:

- [`playwright.spec.js`](../../artefact/files/role/playwright.specs.js.md): what the role-local spec MUST contain (entry point, scenarios, selectors, final state)
- [`playwright.env.j2`](../../../agents/files/role/playwright.env.j2.md): rendered test input surface, variable naming, and entry-point selection

## Recording Tests 🎬

### Playwright Codegen (built-in) 🔧

Playwright ships a built-in code recorder:

```bash
npx playwright codegen https://<app-url>
```

This opens the Playwright Inspector alongside a browser. Every interaction is recorded and emitted as a runnable spec. Use the output as a starting draft and clean it up according to the authoring rules in [`playwright.spec.js`](../../artefact/files/role/playwright.specs.js.md).

### playwright-recorder (Docker-based) 🐳

For infrastructure-heavy setups where Playwright should not live in the main repository, use [playwright-recorder](https://github.com/kevinveenbirkenbach/playwright-recorder). It wraps Playwright codegen in Docker with X11/XWayland forwarding and an ephemeral workspace so no state leaks between recordings.

Requirements: Docker, X11 or XWayland, `xhost`

```bash
# Install
make install

# Record a flow starting at a specific URL
make codegen
# or directly:
./scripts/codegen.sh https://<app-url>/login

# Replay a recorded spec headlessly
make replay
# or directly:
./scripts/replay.sh recordings/login.spec.ts
```

Generated files are persisted in the local workspace (git-ignored). Copy the relevant parts into `files/playwright.spec.js` and adapt them.

## Development Procedure 📋

This page owns framework and runner mechanics only. The procedure for writing, deploying, and reviewing a role-local spec lives in the dedicated SPOTs:

- [Agent `playwright.spec.js`](../../../agents/files/role/playwright.spec.js.md): authoring procedure and live review.
- [Role Loop](../../../agents/action/iteration/role.md): baseline deploy, redeploy rules, Certificate Authority trust, Inspect-before-redeploy.
- [Playwright Spec Loop](../../../agents/action/iteration/playwright.md): spec-only inner loop against the already-running stack.
- [`playwright.spec.js` (role file rules)](../../artefact/files/role/playwright.specs.js.md): what the spec MUST contain, including logged-out final state and console cleanliness.
