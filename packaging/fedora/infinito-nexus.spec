Name:           infinito-nexus
Version:        7.0.0
Release:        1%{?dist}
Summary:        Meta package for Infinito.Nexus host dependencies

License:        LicenseRef-Infinito-Nexus-Community-License
URL:            https://github.com/kevinveenbirkenbach/infinito-nexus
BuildArch:      noarch

Requires:       ansible-core
Requires:       bash
Requires:       ca-certificates
Requires:       curl
Requires:       dbus
Requires:       (docker-ce-cli or docker or moby-engine)
Requires:       docker-compose-plugin
Requires:       gettext
Requires:       git
Requires:       jq
Requires:       make
Requires:       openssh-clients
#
# EL9 AppStream exposes only python3.9 via the generic python3 capability.
# In those environments we still bootstrap Python 3.11+ separately via
# roles/dev-python/files/install.sh, but the RPM metadata must remain
# installable from the stock distro repositories.
%if 0%{?rhel} == 9
Requires:       python3
%else
Requires:       python3 >= 3.11
%endif
Requires:       python3-pip
Requires:       python3-pyyaml
Requires:       rsync
Requires:       sudo
Requires:       systemd
Requires:       tar
Recommends:     bind-utils
Recommends:     shellcheck
Recommends:     shfmt

%description
This package installs the OS-level dependencies required by Infinito.Nexus
development and CI workflows (make, Python, Docker CLI, Ansible controller
tooling, and helper utilities). It intentionally ships no application binaries.

%prep
:

%build
:

%install
install -d %{buildroot}%{_docdir}/%{name}
: > %{buildroot}%{_docdir}/%{name}/DEPENDENCIES

%files
%doc %{_docdir}/%{name}/DEPENDENCIES

%changelog
* Fri May 08 2026 Kevin Veen-Birkenbach <kevin@veen.world> - 7.0.0-1
- * This major release migrates every role to the new meta/ layout with explicit per-role networks, ports, run_after, and info.yml metadata, introduces a variant-aware matrix-deploy planner, ships a process-wide YAML / file / registry caching stack, promotes 13+ apps from alpha to beta, and adds a lint corpus that pins the new conventions in CI.

**Major Changes**

* Migrated every role's meta/ to the req-008/009/010/011 layout: per-role services.yml is the single source of truth for service flags, server.yml carries per-role local subnets, ports live next to the service that owns them, run_after / lifecycle move next to the entity, and a new meta/info.yml carries non-Galaxy descriptive metadata
* Replaced the legacy single-pass deploy with a variant-aware combined resolver and per-round include path: each role can declare a meta/variants.yml, the matrix-deploy planner produces one folder per round, and Playwright specs run once per variant
* Routed every YAML touchpoint and every project-tree walk through utils.cache.{yaml,files} and consolidated the cache modules into a single utils/cache/ package; integration tests now share one parse and one walk per make test invocation
* Promoted 13 web-app roles from alpha to beta with full per-role baselines: native OIDC for Joomla via plg_system_keycloak, in-role login-broker for Bluesky (variant A+), real OIDC integration for four further roles, and the matching Playwright SSO coverage
* Added two new pull-through caches: a Sonatype Nexus 3 OSS package cache (req-012) and a registry cache with TLS frontend, override-only gating, and dev-only Compose profiles

**Added**

* Added new application roles: web-app-opencloud and web-app-opentalk with shared OIDC + LDAP, web-app-hugo for static-site hosting (req-016), web-app-moodle self-built image with OIDC+LDAP hybrid and LDAP-only variants (req-015), web-app-fediwall as multi-wall public-timeline aggregator, plus web-app-mig and web-app-sphinx E2E coverage
* Added the per-role matrix-deploy variant model with folder-per-round inventories, meta/variants.yml declarations, and variant-aware Playwright env wiring
* Added hierarchical /roles/<app>/<role> RBAC paths, service-gated Playwright specs, and the WordPress ↔ Discourse round-trip flow
* Added lookup(email) as the shared SMTP resolution layer and wired email integration into pretix, gitlab, openwebui, flowise, and others
* Added the package-cache (Nexus 3 OSS) and registry-cache stacks with inner-build override, TTL env vars, and SPOT documentation
* Added the diff-driven app whitelist for deploy tests, the unified # noqa / # nocheck suppression grammar, and the info.yml per-role metadata file
* Added web-app-keycloak per-app mapper SPOT via filter plugin and shell-script extraction; OpenLDAP schema for Moodle; web-app-mediawiki install/update via composer_install_extension.sh
* Added new lint guards: project-walk, cache-read, project-root-import, noqa-only-ruff-codes, no-direct-yaml, no-inline-multiline-php-in-sh, no-inline-multiline-sql, no-lookup-config-jinja-default, role-meta-layout, web-role-no-web-dependency, run-once-on-shared-services, redundant-bool-patterns, sed-escape, no-sh-pipefail, compose-resource-limits, dynamic-flag, auth-coverage, variant-coverage, variants-services-match

**Changed**

* Routed every yaml.safe_load / yaml.safe_dump / glob.glob / os.walk / Path.rglob / Path.read_text callsite in tests through utils.cache.{yaml,files} so the project walk and reads are shared across the pytest session
* Reworked the combined resolver to be variant-aware, dropped non-Galaxy keys (license_url, repository, documentation) from meta/main.yml, and consumed web-svc-html via the service registry from web-svc-legal
* Registered web-app-{mastodon,friendica,pixelfed} as shared services for the Fediwall aggregator
* Consolidated update to a single role with per-package-family task files; replaced the MODE_CI flag with a direct RUNTIME check
* Pinned image versions explicitly: SuiteCRM PHP 8.2, Nextcloud 33-fpm-alpine, Moodle PHP 8.3-fpm, Hugo nginx 1.30.0-alpine; opted Ubuntu's docker-compose-v2 out of the package selection
* Migrated Decidim, OpenLDAP schema, Postgres grant-schema, Fider, Odoo OIDC, and svc-db-postgres SQL into dedicated files/*.sql so the inline-multiline-SQL lint stays at zero
* Tightened the compose-resource-limits lint and reconciled the entire role corpus against it
* Adopted the unified # nocheck: <kebab-rule> suppression marker repo-wide; reserved # noqa: for real ruff/flake8 codes

**Fixed**

* Fixed Joomla admin-password handling ($ no longer eaten by bash), plugin manifest waits, and Playwright login hardening
* Fixed Moodle deploy: PHP 8.3-fpm pin, serialized PHP-ext build to avoid modules/ race, dropped msmtp from the FPM healthcheck, aligned meta/services.yml with the image+version mirror convention
* Fixed Nextcloud Talk admin spec, Settings-menu locator drift, Metadata plugin incompatibility, OIDC alt-login click, and the files_bpm plugin entry
* Fixed WordPress multisite wp-config quoting, hardcoded plugin-enable lookups, discourse-integration ordering, and per-variant Discourse toggle gating
* Fixed Mig + Sphinx container_port pointing at a non-existent flat .port key (added a wildcard-path validator)
* Fixed OpenCloud / OpenTalk Playwright OIDC scenarios; added the OpenTalk recorder; fixed OpenCloud SPA wait after the OIDC callback
* Fixed Discourse asset compilation by setting DISCOURSE_FORCE_HTTPS; marked Discourse as a discourse-service provider; dropped the WordPress run_after dep
* Fixed env-test suites: dynamic Fedora release resolution in the cache probe, compose-network discovery for the DiD probe, and oauth2-proxy allowed_groups slash normalization
* Fixed meta drift: req-008 sweep gaps (lost suppressions, silent test breakage, one prod bug), host-bound port collisions on 8071/8072, subnet collisions on 192.168.105.{48,64}/28, and Moodle resource limits
* Fixed utils.cache Ansible coupling: data is importable without ansible, the GID resolver works without ansible, and the YAML cache invalidates per-path entries when mtime/size changes
* Fixed the sys-svc-container package selection on Ubuntu; the Makefile clean target is resilient to container-owned __pycache__ files
* Fixed Bluesky cross-variant recovery + URL-test failures (req-013)

**CI and Tests**

* Added a diff-driven app whitelist so deploy tests run only against roles touched in the change
* Added the lint corpus for: project-walk / cache-read / project-root-import / no-direct-yaml / no-inline-multiline-php-in-sh / no-inline-multiline-sql / no-lookup-config-jinja-default / role-meta-layout / web-role-no-web-dependency / run-once-on-shared-services / redundant-bool-patterns / sed-escape / no-sh-pipefail / compose-resource-limits / dynamic-flag / auth-coverage / variant-coverage / variants-services-match / Ansible Galaxy schema / inline literal script-block size cap / production Python file-size cap / SPOT-of-truth for domain literals / oauth2 proxy-port allocation
* Added the unified # noqa / # nocheck suppression grammar and the noqa-only-ruff-codes guard that forbids project rules in # noqa:
* Routed every fixture write through utils.cache.yaml.dump_yaml and every fixture read through utils.cache.files.read_text
* Added the rbac-group-path static guard, the run-once guard for shared service-registry roles, the Mattermost SSO-button + onboarding dismissal coverage, and the WordPress discourse-roundtrip + finally-cleanup-bound spec
* Promoted the docker-raw-call guard onto the unified suppression grammar and scoped it to roles/
* Centralized INFINITO_DISTRO / INFINITO_CONTAINER SPOT and moved INFINITO_MAKE_DEPLOY defaults into scripts/meta/env/ci.sh

**Contributors**

* [Kevin Veen-Birkenbach](https://www.veen.world/)

* Sat Apr 25 2026 Kevin Veen-Birkenbach <kevin@veen.world> - 6.0.0-1
- This release expands the application portfolio with new civic, ERP, feedback, and observability roles, replaces legacy generated runtime data with lookup-driven configuration and service loading, broadens Playwright end-to-end coverage across the stack, and hardens CI, local development, and deployment reliability.

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

* Thu Mar 19 2026 Kevin Veen-Birkenbach <kevin@veen.world> - 5.1.0-1
- Add packaging metadata for Debian, Fedora and Arch.
- Centralize OS dependency declarations for Infinito.Nexus host workflows.
