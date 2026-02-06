# Test: E2E Cypress Runner 🧪🌐

## Description

This Ansible role provides a **generic, reusable Cypress end-to-end (E2E) test runner**
for the Infinito.Nexus ecosystem.

It automatically discovers roles that ship a Cypress test project under:

- `roles/<application_id>/tests/cypress/`

A role is considered Cypress-enabled if it provides:

- `roles/<application_id>/tests/cypress/env.j2`

The role then stages the Cypress project to a local staging directory, renders a `.env` file
from `env.j2`, optionally waits until the application is reachable, and executes Cypress
inside a pinned Docker image.

---

## Overview

This role:
- Discovers Cypress-enabled roles by scanning `roles/*/tests/cypress/env.j2`
- Supports allow-/deny-lists via `TEST_E2E_ONLY_ROLES` and `TEST_E2E_SKIP_ROLES`
- Stages each Cypress project into `TEST_E2E_STAGE_BASE_DIR/<application_id>`
- Renders `.env` from `env.j2` using Ansible variables (`application_id`, `domains`, `users`, `applications`)
- Optionally waits until the application responds with HTTP `200` or `302`
- Runs Cypress in Docker (`cypress/included:…`) with stable browser settings (`--ipc=host`, `--shm-size=1g`)
- Stores per-role reports/artifacts under `TEST_E2E_REPORTS_BASE_DIR/<application_id>`

---

## Purpose

The purpose of this role is to provide a **central E2E test primitive** that can be executed
at the end of a deployment (e.g., as a post task), without hardcoding tests in the runner itself.

Each application role stays responsible for its own Cypress tests and configuration.
This role only provides the execution framework.

---

## Role Contract (What application roles must provide)

A Cypress-enabled role must provide:

```

roles/<application_id>/tests/cypress/
    env.j2
    volume/

```

Everything else (specs, config, dependencies) is owned by the application role.
Recommended Cypress layout:

```

roles/<application_id>/tests/cypress/
    cypress.config.mjs
    cypress/
        e2e/
        support/

```

### `env.j2`
`env.j2` is rendered into `.env` and passed to Cypress via `--env-file`.

Inside `env.j2` you can resolve the application domain via:

- `{{ lookup('domain',application_id) }}`

---

## Variables

### Staging & Reports
- `TEST_E2E_STAGE_BASE_DIR` (default: `/tmp/test-e2e-cypress`)
- `TEST_E2E_REPORTS_BASE_DIR` (default: `/var/lib/infinito/logs/test-e2e-cypress`)

### Cypress runtime
- `TEST_E2E_IMAGE` (default: `cypress/included:13.6.6`)

### Readiness wait
- `TEST_E2E_WAIT_ENABLED` (default: `true`)
- `TEST_E2E_WAIT_RETRIES` (default: `30`)
- `TEST_E2E_WAIT_DELAY` (default: `5`)

### Discovery filters
- `TEST_E2E_ONLY_ROLES` (default: `[]`)
- `TEST_E2E_SKIP_ROLES` (default: `[]`)

---

## Design Notes

* The role is intentionally **test-agnostic**: it does not ship any concrete Cypress tests.
* `env.j2` acts as the single stable marker for discovery and as the source of environment configuration.
* Cypress is executed in Docker for reproducibility and consistent browser dependencies.

---

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**
Learn more at [www.veen.world](https://www.veen.world)

Part of the **Infinito.Nexus Project**
🔗 [https://s.infinito.nexus/code](https://s.infinito.nexus/code)
