## [6.0.0] - 2026-04-25

* This release expands the application portfolio with new civic, ERP, feedback, and observability roles, replaces legacy generated runtime data with lookup-driven configuration and service loading, broadens Playwright end-to-end coverage across the stack, and hardens CI, local development, and deployment reliability.

**Major Changes**

* Added major new application roles including web-app-odoo, web-app-decidim, web-app-fider, and web-app-prometheus
* Replaced legacy generated applications / users setup flows with cached lookup-driven runtime data, centralized service-registry semantics, and nested compose.services.* configuration paths
* Replaced the legacy Cypress-based browser test path with the dedicated test-e2e-playwright role and role-local Playwright specs / env files
* Expanded shared platform integrations for SMTP, Prometheus / native metrics, OIDC, LDAP, and role-based RBAC provisioning
* Hardened CI and local development with better WSL2 bootstrap support, safer swap / disk handling, stronger GHCR mirroring and release workflows, and updated fork / PR automation

**Added**

* Added web-app-odoo with Docker Compose deployment, Redis integration, LDAP support, Keycloak / OIDC auto-provisioning, HTTPS-safe OAuth customization, and Playwright login / logout coverage
* Added web-app-decidim with dedicated Docker image, OIDC bootstrap wiring, Ruby helper scripts, administrator setup, and Playwright coverage
* Added web-app-fider as a new feedback platform role with deployment, OIDC setup, and end-to-end browser coverage
* Added web-app-prometheus with alerting, alertmanager, blackbox, UI integration assets, and Playwright coverage
* Added the dedicated test-e2e-playwright runner role plus broad new Playwright suites for apps including Pixelfed, Taiga, Mailu, Mattermost, Friendica, Joomla, Odoo, Decidim, PeerTube, Nextcloud, Matrix, BigBlueButton, and dashboard-linked flows
* Added lookup(email) as the shared SMTP resolution layer and wired email integration into roles such as openwebui, flowise, pretix, and gitlab
* Added generic OIDC group-to-RBAC auto-provisioning for WordPress through OpenLDAP-backed role mapping
* Added issue templates, split PR templates by contribution type, and introduced CODEOWNERS
* Added broader GHCR tooling including mirror cleanup, Docker image version fixing, and release / update workflow helpers

**Changed**

* Migrated runtime resolution away from legacy generated dictionaries and setup CLIs toward cached lookup plugins such as applications, users, domains, image, service, and service_registry
* Reworked shared service discovery and loading around the new sys-utils-service-loader flow and the required service semantics
* Reorganized role configuration toward clearer service-scoped keys under compose.services.*
* Extended Docker image version handling to support ghcr.io, depth-aware comparisons, and flavored semver tags such as 5.4.5-php8.3-apache
* Expanded Prometheus / native metrics integration across application roles, especially communication-oriented apps
* Reworked contributor, agent, and operations documentation into granular SPOT-style guides covering workflow, testing, debugging, sandboxing, PR creation, and environment setup
* Improved WSL2 and local development bootstrap flow with better Docker, DNS, CA trust, package installation, and smoke-test coverage
* Adopted git-maintainer-tools for fork / upstream remote routing and signed-push workflow handling

**Fixed**

* Fixed the Joomla install / re-deploy flow across the open regression classes: raw-git-tree refusal handling, re-deploy idempotency, dash pipefail incompatibility, cleanup-phase crashes, and fresh-install password-reset races
* Fixed PeerTube plugin-install reliability with explicit image pinning, improved diagnostics, memory-cap-aware install handling, and local OOM reproduction support
* Fixed Mattermost SSO button regressions, Mailu DNS behavior, Nextcloud Talk TURN publishing, Friendica LDAP addon activation, Baserow bootstrap timing, BigBlueButton database race conditions, and multiple Odoo OAuth / provisioning edge cases
* Fixed GHCR mirror visibility publication, propagation timing, and authenticated package handling
* Fixed PR / branch cancellation behavior, branch-scope CI gating, fork prerequisite handling, and several GitHub Actions orchestration edge cases
* Fixed multiple domain, CSP, email, lookup, and proxy wiring issues uncovered during the applications / users migration

**CI and Tests**

* Added the external Docker image version-check workflow, a weekly CodeQL safety cron, dedicated PR close / branch delete cancel workflows, and stronger development-environment testing
* Expanded lint, unit, and integration coverage around service-registry behavior, compose resource limits, email integration requirements, no_log policy, lookup usage, min-storage validation, and non-bash pipefail regressions
* Improved CI diagnostics, runner-state dumps, disk / swap handling, image wait logic, and mirror / release backfill workflows for fork-based development
* Centralized more CI helper logic into reusable scripts and utility modules to reduce workflow duplication

**Contributors**

* [Kevin Veen-Birkenbach](https://www.veen.world/)
* [Alejandro Roman](https://github.com/AlejandroRomanIbanez)
* [Evangelos Tsakoudis](https://github.com/evangelostsak)
* [Prageeth Panicker](https://github.com/pragepani)


## [5.2.0] - 2026-03-21
* This minor release adds Mattermost deployment support, improves release image automation, and hardens CI, Ansible plugin handling, and application deployment reliability across the stack.
**Added**
* Added *web-app-mattermost* with Docker Compose deployment, PostgreSQL support, Keycloak-based SSO via the GitLab OAuth2 provider, and optional Mailu integration
* Added retry-capable *uri_retry* and *get_url_retry* action plugins with dedicated unit and integration test coverage
* Added a scheduled/manual workflow to backfill the highest missing release image tag in GHCR
* Added a pull request template and consolidated contributor workflow documentation
* Added Manjaro ID support
**Changed**
* Reorganized custom Ansible plugins into the unified *plugins/* layout
* Moved backend service-load decisions into a dedicated lookup plugin
* Increased Nextcloud Talk and Talk Recording resources and made upload size handling configurable
* Reworked image build, push, mirror, wait, and release helper scripts for clearer repository and distro resolution
* Pinned Docker GitHub Actions used in release image workflows to commit SHAs
* Hardened *baserow* by pinning the image version to *2.1.6*
**Fixed**
* Fixed Mailu admin readiness checks and reduced Mailu deploy race conditions in CI
* Fixed flaky Nix-related network failures and added explicit failure-path coverage for retry handling
* Fixed *strong_password* filter *module_utils* resolution
* Fixed reusable workflow wait parameter wiring and test-dns CI image selection
* Fixed GHCR namespace lowercasing edge cases in image-related workflows
* Added deeper Matomo bootstrap failure diagnostics for easier troubleshooting
**CI and Tests**
* Refactored fork PR image handling to safely build, mirror, and validate CI images for external contributions
* Improved GHCR publish authentication, source linking, and source labels on pushed CI images
* Added explicit prebuilt-image wait errors and clearer release-image backfill detection
* Reduced false CI failures by skipping cleanup during the second deploy pass
* Expanded lint, unit, and integration coverage around retry plugins and plugin path usage
**Contributors**
* [Kevin Veen-Birkenbach](https://www.veen.world/)
* [Alejandro Roman](https://github.com/AlejandroRomanIbanez)
## [5.1.0] - 2026-02-28
* This minor release improves cross-distro package handling, hardens CI reliability, fixes Ansible compatibility issues, and adds clearer contributor and local test workflows.
**Added**
* Introduced *docs/guides/developer/CONTRIBUTION_WORKFLOW.md* with fork-based workflow, mandatory green fork CI before PRs, and merge policy guidance
* Added the single-app local deploy wrapper and related local test documentation
* Added *min_storage* entries for warned roles
**Changed**
* Made *dev-base-devel* distro-aware for default distros
* Removed hardcoded *base-devel* from workstation bundles and *sys-aur*
* Set *drv-epson-multiprinter* lifecycle to *pre-alpha*
* Refactored *dev-fakeroot* by extracting *01_core* tasks
* Documented local *make check* targets
**Fixed**
* Fixed *sys-aur-install* name/upgrade clash
* Enabled EPEL for *dev-fakeroot* on CentOS
* Made *drv-intel* VA-API package handling distro-specific
* Fixed undefined *run_once* lookup in backend service loader
* Restored DB seed enablement semantics without bool-coercion warning
* Fixed Ansible fact deprecations and loop variable collisions
**CI and Tests**
* Added retries for Docker-in-Docker DNS handling
* Added retry loop for buildx push
* Aggressively pruned Docker artifacts between distro runs
* Removed deprecated buildx install input
## [5.0.0] - 2026-02-25
* * **Supported distributions:** *Fedora*, *CentOS*, *Ubuntu*, *Debian*
* **Breaking Changes:** Migration from *util-* to bundle inventories under *inventories/bundles/*; deployments must migrate to new bundle and role names. Central package and AUR model via *SYS_PACKAGES* and *SYS_AUR_PACKAGES*; new roles *sys-aur* and *sys-aur-install*; renames including *util-desk-dev-core* to *dev-core*, *util-desk-dev-python* to *dev-python*, *util-desk-dev-arduino* to *dev-arduino*; *util-srv-corporate-identity* removed.
* **Added:** New workstation bundles (*admin*, *admin-network*, *browser*, *design*, *dev-arduino*, *dev-core*, *dev-java*, *dev-php*, *dev-python*, *dev-shell*, *game-compose*, *game-os*, *game-windows*, *office*). Inventory driven *sys-package* role with constructor auto load when *SYS_PACKAGES* is set. New roles *sys-openssl* and *sys-aur-install*. New lookup plugin *command_path*. New variable *SOFTWARE_URL* and updated login banner.
* **Changed:** Default distribution switched to *Debian* and CI image handling aligned. Python baseline raised: *dev-python* installs Python 3.11+ by default; *requires-python* raised to *>=3.11*. Cross distro Python interpreter and pip handling unified via *sys-pip-install*. Dashboard deployment uses fixed image *ghcr.io/kevinveenbirkenbach/port-ui:1.0.0* and mounts generated *config.yaml* read only. Alerting hardened with explicit timeouts for compose and email, plus portable mailer and systemd instance fallbacks.
* **Fixed:** OpenProject migrations stabilized (simplified migration step; preload *CustomFieldContext* before *db:migrate*). Nextcloud LDAP config hardened and incompatible apps disabled in production. XWiki extension install hardened and one time seed ensures *Main.WebHome* exists. Matomo bootstrap fails fast on root cause. TLS and CA improvements (unified self signed CA env for health services, retries for CA trust override generation, Nix TLS CA trust fix). *msmtp* improved on Fedora. OpenLDAP *python-ldap* build prerequisites and header fallback refactored; per user *password_update* policy added. Backup and ops fixes (OnlyOffice no restart during backups; backup home and ACL tasks more reliable). Container setup hardened (Fedora Docker CE CLI, dnf5 repo add, Debian buildx conflict fix, Docker readiness and SSH restart improvements).
* **CI and Tests:** New integration tests for portable python shebangs, forbid *sh -lc* with *pipefail*, and improved variable checks. CI stability improvements for per distro stacks and mirror resolver via venv Python, plus more robust package manager retries.
## [4.1.0] - 2026-02-17
* **Added**
* Controller-side *version* lookup plugin reading from *pyproject.toml* (with Poetry fallback)
* New *unit_name* lookup plugin for consistent versioned systemd unit generation
* Automatic prune phase in *sys-service* (stop/disable outdated units, remove old unit files, trigger daemon-reload)
* Persist application version as *INFINITO_VERSION* in */etc/environment*
* Parameterized image and version handling for *web-svc-simpleicons*
* Introduced *entity_name* derived from *application_id*
**Changed**
* *sys-service* now uses *SOFTWARE_DOMAIN* instead of *SOFTWARE_NAME* for versioned units
* Reordered service lifecycle: *prune → lockdown → reset*
* Refactored internal task structure for clearer execution flow
* Made */etc/environment* path configurable
**Removed**
* Legacy *FILE_VERSION* mechanism
* Deprecated *get_service_name* filter
* Legacy *simpleicons_host_* variables
## [4.0.3] - 2026-02-16
* Try Matomo Boostrap 7 times if errors occure
## [4.0.2] - 2026-02-15
* Matomo upgrade to 1.1.13
## [4.0.1] - 2026-02-15
* This release focuses on improving Matomo installation stability, aligning base images, and introducing automated CI image cleanup.
**Improvements**
* Upgraded *matomo-bootstrap* to v1.1.12 and aligned with the latest Matomo version
* Increased installer stability with explicit timeout environment variables
* Extended timeout for the flaky *setupSuperUser* step
* Properly quoted *MATOMO_ADMIN_PASSWORD* in bootstrap environment
* Removed obsolete debug code referencing a non-existent *--debug* parameter
**Base Image Changes**
* Changed default distribution from Arch → Debian (slimmer, better aligned with published images)
* Refactored *mig* to use the published image and aligned Debian aliases
* Fixed integration tests
**CI Enhancements**
* Renamed mirror workflows (*mirror-images-* → *images-mirror-*)
* Added automated weekly + manual GHCR cleanup workflow
* Cleanup removes only *ci-* tagged images older than 7 days
* Extracted cleanup logic into a dedicated script
* Supports both user and organization GHCR registries
**Result**
More stable Matomo installations, leaner base images, and improved CI image lifecycle management.
## [4.0.0] - 2026-02-13
* **Breaking Changes**
* Renamed *compose.services.desktop* to *compose.services.dashboard*
* Renamed role *web-app-desktop* to *web-app-dashboard*
  → Custom inventories and overrides must be updated accordingly
**Added**
* Introduced bundle-based server inventories under *inventories/servers/*
**Changed**
* *DOMAIN_PRIMARY* is now strictly validated (especially for Dashboard and OpenResty)
* Homepage domain is resolved automatically (Dashboard domain is preferred if present)
## [3.0.0] - 2026-02-11
* **🚨 Breaking Changes**
* Deployment type flag removed
  The CLI flag *-T / TEST_DEPLOY_TYPE* has been removed. Deployment types are now derived automatically from invokable role rules.
* Universal stage execution removed
  Universal roles are no longer executed as a separate lifecycle stage. They are handled exclusively via constructor and destructor stages. This prevents duplicate executions but changes lifecycle behavior.
* Removed CLI flags
  The following options are no longer available:
  *--sound*
  *--no-signal*
  *--alarm-timeout*
* CI filtering changed
  *ONLY_APP* has been replaced with a space-separated *WHITELIST*.
  *INCLUDE_RE* and *EXCLUDE_RE* have been removed.
  Lifecycle selection via *TESTED_LIFECYCLES* is no longer supported.
* Web-App Chess deployment changed
  The custom Dockerfile was removed.
  The service now uses a prebuilt registry image.
  Runtime *yarn install* no longer runs during container startup.
---
**⚠ Behavior Changes**
* Deployment type detection
  Deployment types server, workstation, and universal are now derived strictly from centralized invokable rules. Inventory group aliases are no longer interpreted.
* Matomo healthcheck behavior
  Healthchecks were reworked.
  HTTP readiness validation is stricter.
  Bootstrap now retries before failing.
  Container health timing differs from previous versions.
* OpenResty image handling
  Image and version are now resolved from role configuration instead of hardcoded variables. Custom overrides must be placed in config.
* Docker command abstraction
  Direct *docker exec* usage was replaced with *container exec*. Custom scripts relying on raw docker commands may require adjustment.
* CI release triggering
  Release logic is now driven by commit tags instead of tag-push events.
---
**🧹 Removed**
* Sound subsystem
* Deprecated lifecycle filtering logic
* Legacy matrix text-based filtering
* Obsolete CLI and CI parameters
## [2.1.9] - 2026-02-10
* Matomo now waits for a real HTTP-ready state before bootstrapping, replacing the TCP check with a PHP-based /index.php healthcheck to prevent startup race conditions.
## [2.1.8] - 2026-02-09
* Add SSH client to the CI Docker image so Ansible controller runs no longer fail due to a missing ssh binary.
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
### Release: Infrastructure Hardening, Mirroring & Deterministic Deploys 🚀
This release delivers a major stability and reliability upgrade across the Infinito.Nexus ecosystem. It focuses on **deterministic deployments**, **robust TLS/CA handling**, **mirror-aware inventories**, and **CI/CD resilience**, while standardizing Docker service configuration across roles.
### Highlights ✨
#### TLS & Certificate Pipeline 🔐
* Switched self-signed mode to a **CA-signed certificate chain** with deterministic trust installation
* Strict SAN planning driven by `CURRENT_PLAY_DOMAINS_ALL`
* Clean separation of TLS state (`tls`) and cert paths (`cert`)
* Faster, safer cert deployment (no global sleeps, deterministic container restarts)
* Improved domain/alias resolution and strict opt-in auto-alias behavior
#### CA Trust Injection (Host & Containers) 🧩
* Unified trust injection via `with-ca-trust.sh`
* Best-effort CA installation (non-fatal in minimal/unprivileged containers)
* Env-based trust fallbacks (`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, …)
* Support for distroless images, profile-only services, NSS/Chromium
* Hardened CA override generator and correct execution order
#### Docker Compose Tooling 🐳
* Centralized and hardened compose wrappers (`compose-base`)
* Strict multi-pass Jinja rendering to prevent leaked templates
* Correct `--env-file` handling and safe argument escaping
* Deterministic compose behavior across local, CI, and containerized environments
#### Inventory & Image Mirroring 🪞
* New `--mirror` support for inventory generation
* Per-service `mirror_policy`:
  * `if_missing` (default)
  * `force`
  * `skip`
* Mirrors override **image/version only**, preserving all other service config
* Robust GHCR mirroring with rate limiting, concurrency protection, and recompress fallback
* CI workflows fully mirror-aware with strict env validation
#### Standardized Service Configuration 🧱
* Unified Docker image handling via `docker.services.<service>.image/version`
* Refactored multiple roles (pgAdmin, Friendica, LibreTranslate, oauth2-proxy, Funkwhale, …)
* Removed misleading/deprecated image/version flags (e.g. Nextcloud)
#### CI & Test Guardrails 🧪
* New integration tests enforcing:
  * valid image/version syntax
  * required image tags for buildable services
* Improved CI stability (AppArmor handling, deterministic compose execution)
#### Role Hardening & Idempotency 🛠️
* Reliable admin bootstrap for Discourse, Snipe-IT, Taiga, WordPress
* LDAP/OIDC fixes across multiple services (Nextcloud, Mailu, Snipe-IT, Discourse)
* Resource limits added to prevent OOM crashes
* Safer systemd deploy flow with deploy-safe timer handling
* Improved admin and cleanup tooling
### Why this matters 🧠
* Deployments are now **predictable, repeatable, and debuggable**
* TLS, CA trust, and Docker behavior are aligned across **local, CI, and production**
* Image mirroring is **explicit, controlled, and safe by default**
* Role configuration is **consistent and machine-verifiable**
### Notes ⚠️
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
