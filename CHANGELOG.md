## [2.1.7] - 2026-02-09

* Improves CI stability by extending deploy job timeouts to 6 hours, moving compose pull retries into Ansible, and adding additional deployer metadata.


## [2.1.6] - 2026-02-09

* Improves CI and test robustness by fixing Jinja2 templating edge cases, unifying unittest mock imports, hardening Docker image pull retries, and resolving multiple code-scanning alerts without suppressions.


## [2.1.5] - 2026-02-09

* Prevents CI failures when no workstation apps are discovered by safely skipping the deploy job, and cleans up unnecessary cleanup output to keep logs readable and focused.


## [2.1.4] - 2026-02-08

* This release ensures that commits carrying a version tag trigger the full distro test matrix by detecting tags pointing at the current commit, while regular commits continue to run on a single random distro.


## [2.1.3] - 2026-02-08

* This release improves CI and developer tooling robustness by fixing hardlink-related errors, stabilizing workflow triggers, resolving type-checking import cycles, and hardening cleanup and teardown logic across the CLI and templating utilities.


## [2.1.2] - 2026-02-08

* Removes the v* tag trigger from the push workflow so CI runs only on branch pushes. This prevents duplicate pipeline executions when pushing a branch together with a version tag and aligns the workflow with the updated release process.


## [2.1.1] - 2026-02-08

* Resolved CI instability caused by incomplete Docker cleanup between distro runs


## [2.1.0] - 2026-02-08

* Improves CI and release reliability by simplifying workflows, correcting permission handling, and hardening the pipeline against transient upstream failures.


## [2.0.0] - 2026-02-08

* **Standardized container execution** by fully replacing raw Docker CLI usage with the *container* and *compose* wrappers, enforcing engine-agnostic behavior via integration tests
* **Migrated compose files** from *docker-compose.yml* to *compose.yml*, including override and CA override variants, and unified compose-related configuration keys
* **Centralized compose path resolution** and file argument handling to be deterministic, consistent, and testable
* **Introduced strict lookup APIs** using positional *want-path* semantics for *config*, *container*, *compose*, *tls*, *cert*, *nginx*, *domain*, and *database*
* **Improved CLI testability** by making imports patchable and forwarding command arguments unchanged
* **Hardened CA trust, health, and repair logic** with *soft-fail* behavior, improved diagnostics, and safe handling of one-shot containers
* **Fixed Moodle redeploy failures** by stripping the trailing slash from *CFG->wwwroot* to prevent health check issues
* **Made Snipe-IT admin bootstrap idempotent** and treated known *users_groups* duplicate constraint errors as non-fatal while keeping strict failure handling for other cases
* **Stabilized multi-distro CI deploys** with per-distro orchestration, two-pass *ASYNC* testing, hard cleanup between runs, and a global execution time budget
* **Improved image mirroring workflows** with clearer separation of full and missing-only runs, branch-scoped concurrency, and deploy gating on successful mirroring


## [1.0.0] - 2026-02-03

### 🚀 Release: Infrastructure Hardening, Mirroring & Deterministic Deploys

This release delivers a major stability and reliability upgrade across the Infinito.Nexus ecosystem. It focuses on **deterministic deployments**, **robust TLS/CA handling**, **mirror-aware inventories**, and **CI/CD resilience**, while standardizing Docker service configuration across roles.

### ✨ Highlights

#### 🔐 TLS & Certificate Pipeline

* Switched self-signed mode to a **CA-signed certificate chain** with deterministic trust installation
* Strict SAN planning driven by `CURRENT_PLAY_DOMAINS_ALL`
* Clean separation of TLS state (`tls`) and cert paths (`cert`)
* Faster, safer cert deployment (no global sleeps, deterministic container restarts)
* Improved domain/alias resolution and strict opt-in auto-alias behavior

#### 🧩 CA Trust Injection (Host & Containers)

* Unified trust injection via `with-ca-trust.sh`
* Best-effort CA installation (non-fatal in minimal/unprivileged containers)
* Env-based trust fallbacks (`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, …)
* Support for distroless images, profile-only services, NSS/Chromium
* Hardened CA override generator and correct execution order

#### 🐳 Docker Compose Tooling

* Centralized and hardened compose wrappers (`compose-base`)
* Strict multi-pass Jinja rendering to prevent leaked templates
* Correct `--env-file` handling and safe argument escaping
* Deterministic compose behavior across local, CI, and containerized environments

#### 🪞 Inventory & Image Mirroring

* New `--mirror` support for inventory generation
* Per-service `mirror_policy`:

  * `if_missing` (default)
  * `force`
  * `skip`
* Mirrors override **image/version only**, preserving all other service config
* Robust GHCR mirroring with rate limiting, concurrency protection, and recompress fallback
* CI workflows fully mirror-aware with strict env validation

#### 🧱 Standardized Service Configuration

* Unified Docker image handling via `docker.services.<service>.image/version`
* Refactored multiple roles (pgAdmin, Friendica, LibreTranslate, oauth2-proxy, Funkwhale, …)
* Removed misleading/deprecated image/version flags (e.g. Nextcloud)

#### 🧪 CI & Test Guardrails

* New integration tests enforcing:

  * valid image/version syntax
  * required image tags for buildable services
* Improved CI stability (AppArmor handling, deterministic compose execution)

#### 🛠️ Role Hardening & Idempotency

* Reliable admin bootstrap for Discourse, Snipe-IT, Taiga, WordPress
* LDAP/OIDC fixes across multiple services (Nextcloud, Mailu, Snipe-IT, Discourse)
* Resource limits added to prevent OOM crashes
* Safer systemd deploy flow with deploy-safe timer handling
* Improved admin and cleanup tooling

### 🧠 Why this matters

* Deployments are now **predictable, repeatable, and debuggable**
* TLS, CA trust, and Docker behavior are aligned across **local, CI, and production**
* Image mirroring is **explicit, controlled, and safe by default**
* Role configuration is **consistent and machine-verifiable**

### ⚠️ Notes

* Mirroring remains **opt-in** via `--mirror`
* Strict validation fails fast only where silent misconfiguration would be dangerous
* Several deprecated config paths/tests were removed as part of the standardization


## [0.12.0] - 2026-01-25

* Hardened CI/CD pipelines with retries and Git fallback for Ansible Galaxy collections
* Unified ShellCheck execution via container for reproducible linting
* Enforced secure secret handling across all roles (shell quoting, dotenv, sed safety)
* Introduced `sed_escape` filter to prevent sed injection and config corruption
* Implemented robust, idempotent PostgreSQL superuser password rotation
* Improved Mailu and MariaDB user/password idempotency and CLI safety
* Added optional Django admin bootstrap and secure `SECRET_KEY` handling for Baserow
* Refactored TLS into a single, explicit resolution layer with SAN-aware certificates
* Improved Keycloak reliability by handling noisy CLI output without jq
* Fixed Discourse startup issues by enforcing `C.UTF-8` locale
* Refactored CSP health checks to operate on full URLs derived from NGINX configs (**breaking change**)
* Improved developer experience with cleaner CLI structure, scripts, and tests


## [0.11.0] - 2026-01-10

* CI failures are easier to debug thanks to clear per-app logs and improved error reporting.


## [0.10.0] - 2026-01-08

* **More reliable workstation setups:** A dedicated *workstation user* ensures deployments and integration tests run consistently.
* **Improved user management:** A unified *user_key* model provides clearer and more robust user and permission handling across all roles.
* **Cleaner Docker environments:** Removing implicit cgroup volumes prevents unwanted anonymous volumes and makes container behavior more predictable.
* **New CLI capability:** Automatic resolution of *run_after* dependencies with safe cycle detection simplifies role analysis and automation.
* **More reliable Git configuration:** Git setup now works consistently for workstation users without broken or implicit dependencies.
* **More robust Mailu configuration:** Optional user roles are handled safely, avoiding configuration and runtime errors.


## [0.9.0] - 2026-01-07

* Skip hostname configuration when running inside Docker containers
* Unify workstation user handling via *WORKSTATION_USER* across desktop roles
* Cleanly resolve conflicts between postfix and msmtp for local and external mail delivery
* Consolidate mail configuration using flat *SYSTEM_EMAIL_* variables and improve local delivery reliability
* Make remote backup pulls fail fast per host while continuing across providers
* Enable Nix shell integration by default and finalize the official installer flow
* Improve MediaWiki deployment with persistent extensions and a safer install/update process


## [0.8.0] - 2026-01-06

* Safer failed-backup cleanup (04:00, timeout, single worker; cleanback 1.3.0 semantics).


## [0.7.2] - 2026-01-06

* Introduced lifecycle metadata for roles (`meta/main.yml`)
* Gated CI deploy tests to tested lifecycles only (alpha, beta, rc, stable)
* Bumped `cleanback` to 1.2.1 (timestamp-based force-keep)


## [0.7.1] - 2026-01-06

* Switched web-app-sphinx to a prebuilt container image
  Removed local pkgmgr build logic and now deploys via the published GHCR image with explicit Docker service configuration.

* Stabilized XWiki REST authentication and superadmin provisioning
  Fixed Dockerfile credential injection, introduced shared REST session handling, and ensured consistent cookie and CSRF usage for all REST writes.

* Improved XWiki Ansible idempotency and URL handling
  Normalized internal URLs, clarified uri auth parameters, and made extension install and admin setup fully repeatable.

* Reset logout service database configuration
  Explicitly set database type to null where no persistence is required.

* Restored Ansible task timing and profiling output
  Re-enabled timer and profile_tasks via callbacks_enabled, restoring runtime visibility with YAML output.

* Simplified CI image publishing workflow
  Removed the ci-publish workflow to ensure images are always built on version tags, while keeping stable tagging gated on successful checks.


## [0.7.0] - 2026-01-05

* More reliable releases: versioned Docker images are always built and published; latest always points to the newest version.
* More stable updates: pkgmgr execution is more robust, especially in non-interactive environments and virtual environments.
* Better readability: Ansible output is now shown in clean, human-readable YAML format by default.
* More reliable analytics setup: Matomo is initialized automatically even if the service is unreachable or the API token is missing.
* Improved networking behavior: Docker services now consistently use configurable host addresses instead of hard-coded loopback addresses.

https://chatgpt.com/share/695be0b8-9154-800f-8c03-2bcf3daab157


## [0.6.0] - 2025-12-31

* **SSH keys are now configured in inventory via users.<name>.authorized_keys** (single source of truth). The old CLI option to inject administrator keys and the inventory files-based authorized_keys copy were removed.
* **Administrator login is enforced to be key-based:** playbooks fail early if users.administrator.authorized_keys is empty.
* **Backup user SSH access was hardened:** backup keys are wrapped with a forced command wrapper and written via the shared user role; config is now users.backup.authorized_keys.
* **Token handling was unified:** Mailu and Matomo now read tokens from users.*.tokens (mailu_token legacy removed), and a token-store hydration mechanism loads persisted tokens automatically.
* **Matomo integration is safer:** it now fails fast on empty tokens and consistently uses the hydrated users.administrator.tokens value for API calls.
* **Backup/cleanup services are more reliable:** run-once flags execute earlier, user-backup is an explicit dependency, and cleanback now uses a configurable backups root and keeps the newest backups by default (force-keep=3).
* **Better cross-distro stability:** sys-pip-install now resolves the correct pip executable dynamically and uses ansible.builtin.pip, reducing interpreter/PATH mismatches; plus CoreDNS is a compose dependency and yay auto-rebuilds if the binary is broken after libalpm ABI changes.


## [0.5.0] - 2025-12-30

* Unified TLS handling by replacing SSL_ENABLED with TLS_ENABLED across the entire stack
* Removed localhost special-casing and introduced infinito.localhost as a consistent FQDN
* Stabilized CI deploys via a single make test-deploy entrypoint with INFINITO_DISTRO
* Eliminated Docker container name conflicts by reusing or cleanly resetting deploy test containers
* Fixed systemd-in-container boot hangs by disabling systemd-firstboot and initializing machine-id
* Switched CI execution to compose-native workflows with host cgroup support for systemd
* Hardened Docker and systemd restarts with non-blocking logic, timeouts, and detailed diagnostics
* Fixed SMTP in CI and DinD by dynamically selecting ports and disabling authentication when TLS is off
* Ensured reliable Mailu initialization by waiting for database schema readiness
* Prevented backup failures by enforcing linear service execution order and safer handler flushing
* Removed obsolete legacy paths now that systemd is universally available
* Improved code quality and CI stability through Ruff optimization and test fixes


## [0.4.0] - 2025-12-29

* **CI DNS & Defaults:** Introduced CoreDNS-based *.localhost resolution (A/AAAA to loopback), set DOMAIN_PRIMARY to localhost, added DNS assertions and a strict default 404 vhost to stabilize early CI stages.

* **Docker-in-Docker:** Switched the deploy container to real Docker-in-Docker using fuse-overlayfs, fully decoupled from the host Docker socket and configured a deterministic storage driver.

* **CI Debugging:** Greatly improved CI diagnostics by dumping resolved docker compose configuration and environment data in debug mode, with optional unmasked .env output.

* **Bind Mount Robustness:** Fixed CI-specific bind mount issues, ensured /tmp/gh-action visibility, prevented file-vs-directory conflicts, and asserted OpenResty/NGINX mount sources before startup.

* **Service Orchestration:** Added deferred service execution via system_service_run_final and the new sys-service-terminator, enabling deterministic, end-of-play service execution with built-in rescue diagnostics.

* **Backup Layout:** Consolidated all backups under /var/lib/infinito, parameterized the pull workflow, switched to dump-only backups, and disabled Redis backups across web applications.

* **Database Seeding:** Introduced the * multi-database marker for cluster-aware seeding, enabling clean PostgreSQL cluster dumps and clearer seeder semantics.

* **CSP Health Checks:** Migrated CSP health checks to a Docker-based csp-checker with configurable image selection, optional pre-pull behavior, and improved ignore handling.

* **Tokens & Secrets:** Unified token handling through a centralized token store, added user token defaults, and fully centralized secrets path definitions across roles.

* **Installation Refactor:** Migrated system and backup tooling from pkgmgr and Nix-based installs to system-wide pip installations with clear host vs container separation.

* **Systemd & CI Stability:** Hardened systemd and oneshot service handling in containerized CI, improved exit-code diagnostics, and reduced flaky CI behavior through deterministic execution.

* **Maintenance & Cleanup:** Reduced Let’s Encrypt renewal frequency to avoid rate limits, removed deprecated logs and variables, applied broad refactorings, and merged the Matomo autosetup feature.


## [0.3.5] - 2025-12-21

* SSH client installation is now handled explicitly during user provisioning instead of being bundled into the container build. Root SSH keys are generated in a modular, idempotent way and are preserved across repeated runs. This makes SSH access more predictable, reproducible, and easier to maintain, without changing user-facing behavior.


## [0.3.4] - 2025-12-21

* Added ***sys-util-git-pull*** for deterministic shallow Git updates with tag pinning; integrated into ***pkgmgr***.
* Pinned ***pkgmgr*** clones to ***stable*** for reproducible deployments.
* Refactored CLI to avoid runpy warnings.
* Improved Ansible portability (pacman → package) and added formatter workflow.
* Fixed deploy resolution, AUR installs (use ***aur_builder***), Debian/Ubuntu images (openssh-client), CI rate limits (***NIX_CONFIG***), plus general test and security fixes.


## [0.3.3] - 2025-12-21

* **More reliable installs and deploys:** Fewer Docker and OS-specific failures (especially on CentOS Stream), cleaner container builds, and stable Python/Ansible execution across CI and local environments.
* **Simpler deploy experience:** The deploy command is more predictable and faster because testing is no longer mixed into deploy runs.
* **Fewer “mysterious” errors:** Path, working-directory, and virtualenv issues that previously caused random CI or local failures are fixed.
* **Smoother inventory creation:** Inventory and credential generation now work consistently after refactors, without brittle path assumptions.
* **Overall impact:** Day-to-day usage is more stable, commands behave as expected in more environments, and setup/deploy workflows require less troubleshooting.


## [0.3.2] - 2025-12-19

* Unified cleanup and simplified deploy flow using ***make clean***
* Switched Docker image base to pkgmgr and enforced local images for deploy tests
* Improved CI reliability with reusable workflows, fixed permissions, and consistent SARIF uploads
* Addressed multiple CodeQL and Hadolint findings; applied formatting and security fixes

**Result:** more reproducible builds, cleaner CI, and more robust Docker-based deployments.


## [0.3.1] - 2025-12-18

* Enabled ***pkgmgr install infinito*** test


## [0.3.0] - 2025-12-17

- Introduced a layered Docker architecture: Infinito.Nexus now builds on pre-built pkgmgr base images, with a clear separation between base tooling, application source, and runtime logic.
- Standardized container paths (`/opt/src/infinito`) and switched to a global virtual environment to ensure reproducible builds and consistent test execution.
- Unit and lint tests now run reliably on this new layer model, both locally and in CI.
- Refactored build, setup, and deploy workflows to match the new layered design and improve maintainability.


## [0.2.1] - 2025-12-10

* restored full deployability of the Sphinx app by fixing the application_id scoping bug.


## [0.2.0] - 2025-12-10

* Added full Nix installer integration with dynamic upstream SHA256 verification, OS-specific installation paths, template-driven configuration, and updated pkgmgr integration.


## [0.1.1] - 2025-12-10

* PKGMGR will now be pulled again


## [0.1.0] - 2025-12-09

* Added Nix support role

