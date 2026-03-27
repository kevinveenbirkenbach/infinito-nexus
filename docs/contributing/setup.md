[Back to CONTRIBUTING hub](../../CONTRIBUTING.md)

# Development Environment Setup

Use the repository's real setup flow. The main source of truth is the [Makefile](../../Makefile).

Important:

- Some local development commands change host settings such as [DNS](https://en.wikipedia.org/wiki/Domain_Name_System), [AppArmor](https://en.wikipedia.org/wiki/AppArmor), and [IPv6](https://en.wikipedia.org/wiki/IPv6).
- Some commands use `sudo`.
- Read the setup guides first if you are new to this environment.
- The local development workflow is mainly tested on Linux.

## Platform-Specific Instructions

- [Linux](platform/linux.md)
- [macOS](platform/macos.md)
- [Windows (WSL2)](platform/windows-wsl2.md)

## Shared Repository Workflow

These steps are the shared repository workflow and apply regardless of whether you work on Linux, macOS, or Windows with WSL2.

### Bootstrap

Run these commands from the repository root:

```bash
make bootstrap
make dev-environment-bootstrap
make up
make trust-ca
```

#### Bootstrap Commands

| Phase | Command | What it does |
|---|---|---|
| Initial setup | `make bootstrap` | Installs project dependencies and runs the first repository setup. |
| Host preparation | `make dev-environment-bootstrap` | Prepares the local development machine for the project workflow. |
| Start stack | `make up` | Starts the local development stack. |
| Browser trust | `make trust-ca` | Trusts the generated local [CA](https://en.wikipedia.org/wiki/Certificate_authority) so `*.infinito.example` works correctly in your browser. |

### Teardown

When you are done, use these commands to stop the stack and clean up the local environment:

```bash
make down
make dev-environment-teardown
```

#### Teardown Commands

| Phase | Command | What it does |
|---|---|---|
| Stop stack | `make down` | Stops the local development stack. |
| Host cleanup | `make dev-environment-teardown` | Reverts local development environment changes where supported. |

### Full Development Flow

The repository already contains a development helper script at [development.sh](../../scripts/tests/development.sh). The commands from that file are explained here as the intended end-to-end flow.

#### Flow Summary

| Step | Command | Purpose in this flow |
|---|---|---|
| 1 | `make install` | Installs the dependencies needed before running the local development flow. |
| 2 | `make dev-environment-bootstrap` | Prepares the host machine for local development. |
| 3 | `make up` | Starts the development stack. |
| 4 | `make test` | Runs the main combined validation flow. |
| 5 | `APP=web-app-matomo make test-local-dedicated` | Runs a stronger local validation path for one concrete app. |
| 6 | `make trust-ca` | Makes the generated local certificates trusted by the host browser. |
| 7 | `make down` | Stops the running development stack. |
| 8 | `make dev-environment-teardown` | Cleans up host-side development environment changes. |

Use this as a practical reference when you want to understand how local development is expected to work.

### Minimal Hardware Resources

If you work on a machine with limited CPU, RAM, or disk space, keep the local stack minimal and disable optional services you do not currently need.
This is useful when you focus on one app and do not need Matomo, the dashboard, OIDC, or the logout service during local development.

Example `compose` settings:

```yaml
compose:
  services:
    matomo:
      enabled: false
      shared: false
    dashboard:
      enabled: false
      shared: false
    oidc:
      enabled: false
      shared: false
    logout:
      enabled: false
      shared: false
```

For local deploy shortcuts and end-to-end checks, see [Testing and Validation](testing.md).

