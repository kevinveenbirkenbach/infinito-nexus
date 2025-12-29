## [0.4.0] - 2025-12-29

* * **CI DNS & Defaults:** Introduced CoreDNS-based *.localhost resolution (A/AAAA to loopback), set PRIMARY_DOMAIN to localhost, added DNS assertions and a strict default 404 vhost to stabilize early CI stages.

* **Docker-in-Docker:** Switched the deploy container to real Docker-in-Docker using fuse-overlayfs, fully decoupled from the host Docker socket and configured a deterministic storage driver.

* **CI Debugging:** Greatly improved CI diagnostics by dumping resolved docker compose configuration and environment data in debug mode, with optional unmasked .env output.

* **Bind Mount Robustness:** Fixed CI-specific bind mount issues, ensured /tmp/gh-action visibility, prevented file-vs-directory conflicts, and asserted OpenResty/Nginx mount sources before startup.

* **Service Orchestration:** Added deferred service execution via system_service_run_final and the new sys-service-runner, enabling deterministic, end-of-play service execution with built-in rescue diagnostics.

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

* * Added ***sys-util-git-pull*** for deterministic shallow Git updates with tag pinning; integrated into ***pkgmgr***.
* Pinned ***pkgmgr*** clones to ***stable*** for reproducible deployments.
* Refactored CLI to avoid runpy warnings.
* Improved Ansible portability (pacman → package) and added formatter workflow.
* Fixed deploy resolution, AUR installs (use ***aur_builder***), Debian/Ubuntu images (openssh-client), CI rate limits (***NIX_CONFIG***), plus general test and security fixes.


## [0.3.3] - 2025-12-21

* * **More reliable installs and deploys:** Fewer Docker and OS-specific failures (especially on CentOS Stream), cleaner container builds, and stable Python/Ansible execution across CI and local environments.
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

