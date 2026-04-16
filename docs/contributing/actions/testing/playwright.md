# Playwright Tests 🎭

This page is the SPOT for Playwright end-to-end test requirements, runner integration, and file contracts.
For implementation guidance when writing or updating role-local files, see
[Agent `playwright.spec.js`](../../../agents/files/role/playwright.spec.js.md) and
[Agent `playwright.env.j2`](../../../agents/files/role/playwright.env.j2.md).

## Framework 🧰

- [Playwright](https://playwright.dev/) runs inside Docker via the shared `test-e2e-playwright` role.
- There is no standalone `make` target for Playwright. Tests run as part of local deploy flows
  (e.g. `make deploy-fresh-purged-apps APPS=web-app-matomo FULL_CYCLE=true`).

## When to Write ✍️

- You MUST provide Playwright tests for every `web-*` role.
- You MUST update the Playwright suite when you add or change role-local `javascript.js` or `style.css`.

## Role-Local Files 📁

Every Playwright-enabled role MUST provide exactly these two files:

| File | Purpose |
|---|---|
| `files/playwright.spec.js` | Test scenarios executed by the Playwright runner |
| `templates/playwright.env.j2` | Rendered `.env` passed to the Playwright container |

`package.json` and `playwright.config.js` MUST remain centralized in `roles/test-e2e-playwright/files/`.
You MUST NOT duplicate or override them per role.

## CI Image Source 🪞

The Playwright container image is declared in `roles/test-e2e-playwright/defaults/main.yml` as `mcr.microsoft.com/playwright` with an exact version tag. CI mirrors that image into GHCR through the standard mirror pipeline before deploy tests run, so Playwright jobs do not depend on direct pulls from MCR during the test phase.

The tag MUST stay pinned to an exact Playwright version and distro pair such as `v1.58.2-noble`. You MUST NOT switch this to a mutable tag such as `latest`, because mutable upstream tags are more vulnerable to CDN propagation delays and make flaky CI failures much harder to reason about.

## Runner 🚀

The `test-e2e-playwright` role discovers Playwright-enabled roles through the presence of
`templates/playwright.env.j2`. For each discovered role it:

1. stages the test project
2. renders `.env` from `playwright.env.j2`
3. copies `files/playwright.spec.js` into the project as `tests/playwright.spec.js`
4. injects the shared `package.json` and `playwright.config.js`
5. waits until the app is reachable
6. runs Playwright in Docker

## File Requirements 📄

See the dedicated SPOT pages for authoring rules:

- [`playwright.spec.js`](../../../agents/files/role/playwright.spec.js.md): scenario design, selector strategy, and live review
- [`playwright.env.j2`](../../../agents/files/role/playwright.env.j2.md): rendered test input surface, variable naming, and entry-point selection

## Recording Tests 🎬

### Playwright Codegen (built-in) 🔧

Playwright ships a built-in code recorder:

```bash
npx playwright codegen https://<app-url>
```

This opens the Playwright Inspector alongside a browser. Every interaction is recorded and emitted as a runnable spec. Use the output as a starting draft and clean it up according to the authoring rules in [`playwright.spec.js`](../../../agents/files/role/playwright.spec.js.md).

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

1. Analyze the deployed application in a running local stack.
2. Build hypotheses about the expected user flows before writing tests.
3. Optionally record a draft with Playwright codegen or `playwright-recorder`.
4. Write or update `files/playwright.spec.js` and `templates/playwright.env.j2`.
5. Run the relevant deploy flow (e.g. `make deploy-fresh-purged-apps APPS=<role> FULL_CYCLE=true`).
6. Run `make trust-ca` and open the app in your browser to confirm the flow manually.
7. Inspect the browser console for errors when the flow depends on injected JavaScript.
8. Verify the suite finishes in a logged-out state.
