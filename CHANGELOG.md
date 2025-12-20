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

