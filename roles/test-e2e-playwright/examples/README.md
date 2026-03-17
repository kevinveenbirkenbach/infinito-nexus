# Playwright Central Defaults

This directory provides the central Playwright defaults used by the E2E runner:

- `package.json`
- `playwright.config.js`
- local helper `scripts/record.sh`

Application roles only need:

- `templates/playwright.env.j2`
- `files/playwright.spec.js`

Required in each app role:
- `roles/<application_id>/templates/playwright.env.j2`
- `roles/<application_id>/files/playwright.spec.js`

Central defaults (already provided by `test-e2e-playwright` role):
- `package.json`
- `playwright.config.js`

Then adapt:
- `playwright.env.j2` for environment variables
- `playwright.spec.js` for application-specific checks
- `scripts/record.sh` for local interactive recording with `playwright codegen`

Local recording:
- run `./scripts/record.sh` and answer the role and URL prompts
- from the repository root you can also use:
  `make record-playwright`
- you can also preseed the prompts:
  `ROLE=web-app-nextcloud URL=https://your-app.example make record-playwright`
- extra Playwright CLI flags are passed through, for example:
  `./scripts/record.sh https://your-app.example --target javascript -o tests/login.spec.js`

How it works:
- the script runs `playwright codegen` inside the official Playwright container image
- it uses Firefox by default for better Linux container GUI compatibility; override with `--browser chromium` if needed
- it prompts for the role and URL when needed and writes the generated script to `roles/<role>/files/playwright.spec.js` by default
- it avoids distro-specific Playwright/browser packages on the host
- it supports `container`, `docker`, or `podman`
- it still requires a local graphical session (`DISPLAY` or `WAYLAND_DISPLAY`)
