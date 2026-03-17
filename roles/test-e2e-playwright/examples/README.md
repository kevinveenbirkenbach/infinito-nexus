# Playwright Example Scaffold

Copy this scaffold into an application role:

`mkdir -p roles/<application_id>/tests && cp -r roles/test-e2e-playwright/examples/tests/playwright roles/<application_id>/tests/`

Required for discovery:
- `roles/<application_id>/tests/playwright/env.j2`
- `roles/<application_id>/tests/playwright/volume/`

Then adapt:
- `env.j2` for environment variables
- `tests/*.spec.js` for application-specific checks
- `playwright.config.js` for reporter/timeouts/retries
- `scripts/record.sh` for local interactive recording with `playwright codegen`

Local recording:
- run `./scripts/record.sh https://your-app.example`
- from the repository root you can also use:
  `URL=https://your-app.example make record-playwright`
- extra Playwright CLI flags are passed through, for example:
  `./scripts/record.sh https://your-app.example --target javascript -o tests/login.spec.js`

How it works:
- the script runs `playwright codegen` inside the official Playwright container image
- it uses Firefox by default for better Linux container GUI compatibility; override with `--browser chromium` if needed
- it disables the Playwright inspector window and writes the generated script to `volume/codegen.spec.js` by default
- it avoids distro-specific Playwright/browser packages on the host
- it supports `container`, `docker`, or `podman`
- it still requires a local graphical session (`DISPLAY` or `WAYLAND_DISPLAY`)
