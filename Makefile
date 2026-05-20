.ONESHELL:
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

# SPOT: Global environment is defined in scripts/meta/env/load.sh.
ENV_SH ?= $(CURDIR)/scripts/meta/env/load.sh
export ENV_SH

# For non-interactive bash, BASH_ENV is sourced so the env layer applies to *all* Make recipes.
ifneq ("$(wildcard $(ENV_SH))","")
export BASH_ENV := $(ENV_SH)
else
$(error Missing env file: $(ENV_SH))
endif

.PHONY: setup setup-clean install install-force install-ansible install-lint install-lint-force install-venv install-python install-python-dev install-system-python install-skills update-skills agent-install
.PHONY: test lint lint-action lint-ansible lint-python lint-shellcheck lint-markdown lint-makefile lint-javascript autoformat test-lint test-unit test-integration test-external
.PHONY: clean clean-sudo down cache-clean
.PHONY: system-purge system-disk-usage
.PHONY: list tree mig dockerignore chmod-scripts
.PHONY: print-python
.PHONY: dns-setup dns-remove
.PHONY: environment-bootstrap environment-teardown
.PHONY: wsl2-systemd-check wsl2-dns-setup wsl2-trust-windows
.PHONY: apparmor-teardown apparmor-restore
.PHONY: disable-ipv6 restore-ipv6
.PHONY: trust-ca
.PHONY: restart refresh exec run up down stop
.PHONY: build build-missing build-no-cache build-no-cache-all build-cleanup build-dependency
.PHONY: act-all act-app act-workflow
.PHONY: deploy-fresh-kept-apps container-refresh-inventory deploy-reuse-kept-all container-purge-entity container-purge-system
.PHONY: deploy-fresh-purged-apps deploy-reuse-kept-apps deploy-reuse-purged-apps deploy-fresh-kept-all deploy-bundles redeploy-bundles
.PHONY: bootstrap mark-development

# Bootstrap the local development environment.
environment-bootstrap: wsl2-systemd-check install-python-dev install-lint apparmor-teardown dns-setup disable-ipv6

# Tear down the local development environment.
environment-teardown: apparmor-restore dns-remove restore-ipv6

# Enable systemd on WSL2.
wsl2-systemd-check:
	@bash scripts/system/systemd/enable/wsl2.sh

# Set up DNS on WSL2.
wsl2-dns-setup:
	@sudo bash scripts/system/network/dns/setup/wsl.sh

# Trust Windows certificates in WSL2.
wsl2-trust-windows:
	@bash scripts/system/tls/trust/wsl2.sh

# Configure DNS on Linux.
dns-setup: wsl2-dns-setup
	@bash scripts/system/network/dns/setup/linux.sh

# Remove the DNS configuration.
dns-remove:
	@bash scripts/system/network/dns/remove.sh

# Tear down AppArmor for local development.
apparmor-teardown:
	@echo "==> AppArmor: full teardown (local dev)"
	@if grep -q '^[Yy1]' /sys/module/apparmor/parameters/enabled 2>/dev/null; then \
		sudo bash scripts/system/apparmor/teardown.sh; \
	else \
		echo "[apparmor] AppArmor module is not loaded — skipping teardown"; \
	fi

# Restore AppArmor profiles.
apparmor-restore:
	@echo "==> AppArmor: restore profiles"
	@if grep -q '^[Yy1]' /sys/module/apparmor/parameters/enabled 2>/dev/null; then \
		sudo bash scripts/system/apparmor/restore.sh; \
	else \
		echo "[apparmor] AppArmor module is not loaded — skipping restore"; \
	fi

# Trust the local CA on Linux and WSL2.
trust-ca:
	@bash scripts/system/tls/trust/linux.sh
	@bash scripts/system/tls/trust/wsl2.sh

# Disable IPv6 for local development.
disable-ipv6:
	@sudo bash scripts/system/network/ipv6/disable.sh
	@"$(MAKE)" refresh

# Restore IPv6 settings.
restore-ipv6:
	@sudo bash scripts/system/network/ipv6/restore.sh
	@"$(MAKE)" refresh

# Remove ignored files from the working tree; falls back to sudo for container-owned __pycache__/*.pyc, warns and continues if both fail.
clean:
	@echo "Removing ignored git files"
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		if ! git clean -fdX; then \
			echo "git clean failed (likely container-owned files). Retrying with sudo..."; \
			sudo -n git clean -fdX || { \
				echo "WARNING: sudo cleanup also failed; continuing"; \
				exit 0; \
			}; \
		fi; \
	else \
		echo "WARNING: not inside a git repository -> skipping 'git clean -fdX'"; \
		echo "WARNING: (cleanup continues)"; \
	fi

# Wipe on-disk caches under /var/cache/infinito/core/cache/ (stops cache containers first; re-run `make up` to recreate).
cache-clean:
	@bash scripts/system/cache/clean.sh

# Remove ignored files from the working tree with sudo.
clean-sudo:
	@echo "Removing ignored git files with sudo"
	sudo git clean -fdX;

# Show disk and Docker resource usage to identify what to clean up.
system-disk-usage:
	@bash scripts/system/meta/disk-usage.sh

# Run the broad low-hardware cleanup routine.
system-purge:
	@bash scripts/system/purge/system.sh

# Restart the development stack.
restart:
	@"$${PYTHON}" -m cli.administration.deploy.development restart

# Refresh the running development stack only when it already exists.
refresh:
	@bash scripts/system/network/docker/stack_refresh.sh

# Run a shell (`make exec`) or command (`make exec INFINITO_CMD="..."`) in the running container.
exec:
	@bash scripts/tests/deploy/local/exec/container.sh

# Run a one-off `docker run` inside the running container.
run:
	@bash scripts/tests/deploy/local/exec/run.sh

# Start the development stack.
up: install
	@"$${PYTHON}" -m cli.administration.deploy.development up

# Stop the development stack.
down:
	@"$${PYTHON}" -m cli.administration.deploy.development down

# Stop the development stack without removing volumes.
stop:
	@"$${PYTHON}" -m cli.administration.deploy.development stop

# Mark all shell scripts under scripts/ as executable.
chmod-scripts:
	@find scripts/ -name "*.sh" -exec chmod +x {} \;

# Print the repository role list.
list:
	@echo "Generating the roles list"
	@"$${PYTHON}" -m cli.build.list

# Print the repository tree.
tree:
	@echo "Generating Tree"
	@"$${PYTHON}" -m cli.build.tree -D 2

# Build the meta graph inputs.
mig: list tree
	@echo "Creating meta data for meta infinity graph"

# Build the local image.
build: dockerignore
	@IMAGE_TAG="$$(bash scripts/meta/resolve/image/local.sh)" \
		bash scripts/image/build.sh

# Build the local image if it is missing.
build-missing:
	@IMAGE_TAG="$$(bash scripts/meta/resolve/image/local.sh)" \
		bash scripts/image/build.sh --missing

# Pull the build dependency image.
build-dependency:
	@docker pull ghcr.io/kevinveenbirkenbach/pkgmgr-$${INFINITO_DISTRO}:stable

# Build the local image without cache.
build-no-cache: build-dependency
	@IMAGE_TAG="$$(bash scripts/meta/resolve/image/local.sh)" \
		bash scripts/image/build.sh --no-cache

# Build the no-cache image for every distro.
build-no-cache-all:
	@set -euo pipefail; \
	for d in $${INFINITO_DISTROS}; do \
		echo "=== build-no-cache: $$d ==="; \
		INFINITO_DISTRO="$$d" "$(MAKE)" build-no-cache; \
	done

# Clean up image artifacts.
build-cleanup:
	@bash scripts/image/cleanup.sh

# Regenerate .dockerignore from .gitignore.
dockerignore:
	@echo "Create dockerignore"
	cat .gitignore > .dockerignore
	echo ".git" >> .dockerignore

# Install Ansible dependencies.
install-ansible:
	@ANSIBLE_COLLECTIONS_DIR="$(HOME)/.ansible/collections" \
	bash scripts/install/ansible.sh

# Install lint deps (host/docker via INFINITO_LINT_RUNNER, per-env stamp).
install-lint:
	@bash scripts/install/wrapper.sh

# Force a full lint reinstall (drop the per-env stamp and rebuild it).
install-lint-force:
	@bash scripts/install/wrapper.sh --force

# Install agent skills from skills-lock.json.
install-skills:
	@bash scripts/install/skills/install.sh

# Update all agent skills to latest versions and refresh skills-lock.json.
update-skills:
	@bash scripts/install/skills/update.sh

# Install the system Python prerequisites.
install-system-python:
	@bash roles/dev-python/files/install.sh ensure

# Install the virtual environment.
install-venv: install-system-python
	@bash scripts/install/venv.sh

# Install Python tooling.
install-python: install-venv
	@bash scripts/install/python.sh

# Install Python tooling including lint and dev dependencies.
install-python-dev: install-python
	@bash scripts/install/python.sh dev
	@bash scripts/install/pre-commit.sh

# Install all runtime dependencies, incremental via a stamp file (see scripts/install/all.sh).
install:
	@bash scripts/install/all.sh

# Force a full reinstall (drop the stamp and rebuild it).
install-force:
	@bash scripts/install/all.sh --force

# Install OS-level sandbox dependencies (bubblewrap, socat) required by the Claude Code sandbox.
agent-install:
	@bash scripts/install/sandbox.sh

# Regenerate .env (SPOT) from env/static.env + runtime context (distro, cache sizes, secrets, ...).
dotenv:
	@python3 -m cli.meta.env

# Run the setup step after generating .dockerignore.
setup: dockerignore dotenv
	@bash scripts/setup.sh

# Create the development setup marker.
mark-development: dockerignore
	touch env.development

# Install dependencies and prepare the project.
bootstrap: install setup

# Run setup after cleaning ignored files.
setup-clean: clean setup
	@echo "Full build with cleanup before was executed."

# Run all lint checks in parallel (per-check host/docker via INFINITO_LINT_RUNNER).
lint: install-lint
	@bash scripts/make/parallel.sh lint-action \
		lint-ansible \
		lint-javascript \
		lint-makefile \
		lint-markdown \
		lint-python \
		lint-shellcheck

# Run the GitHub Actions lint checks.
lint-action: install-lint
	@bash scripts/lint/wrapper.sh action

# Run Ansible lint checks (syntax-check + ansible-lint).
lint-ansible: install-lint
	@bash scripts/lint/wrapper.sh ansible

# Run Python lint checks.
lint-python: install-lint
	@bash scripts/lint/wrapper.sh python

# Run shellcheck lint checks.
lint-shellcheck: install-lint
	@bash scripts/lint/wrapper.sh shellcheck

# Run Markdown lint checks via markdownlint-cli2.
lint-markdown: install-lint
	@bash scripts/lint/wrapper.sh markdown

# Run checkmake against the Makefile.
lint-makefile: install-lint
	@bash scripts/lint/wrapper.sh makefile

# Run ESLint over the project's JavaScript files (Playwright specs + persona helpers).
lint-javascript: install-lint
	@bash scripts/lint/wrapper.sh javascript

# Auto-format all source files (skips tools that are not installed).
autoformat: install-lint
	@bash scripts/lint/wrapper.sh autoformat

# Run the full test pipeline (lint + tests) in parallel; fail-fast.
test: install install-lint
	@bash scripts/make/parallel.sh lint test-lint test-unit test-integration

# Run the lint test suite.
test-lint: install
	@INFINITO_TEST_TYPE="lint" \
	INFINITO_COMPILE=0 \
	bash scripts/tests/code/wrapper.sh

# Run the unit test suite.
test-unit: install
	@INFINITO_TEST_TYPE="unit" \
	INFINITO_COMPILE=0 \
	bash scripts/tests/code/wrapper.sh

# Run the integration test suite.
test-integration: install
	@INFINITO_TEST_TYPE="integration" \
	INFINITO_COMPILE=0 \
	bash scripts/tests/code/wrapper.sh

# Run the external test suite.
test-external: install
	@INFINITO_TEST_TYPE="external" \
	INFINITO_COMPILE=0 \
	bash scripts/tests/code/wrapper.sh

# Run all act-based deploy checks.
act-all:
	@bash scripts/tests/deploy/act/all.sh

# Run the act-based app deploy check.
act-app:
	@bash scripts/tests/deploy/act/app.sh

# Run the act-based workflow deploy check.
act-workflow:
	@bash scripts/tests/deploy/act/workflow.sh

# Refresh the container inventory without deploying apps.
container-refresh-inventory:
	@bash scripts/tests/deploy/local/reset/inventory.sh

# Purge one or more app entities from the container.
container-purge-entity:
	@bash scripts/tests/deploy/local/purge/entity.sh

# Purge the broader container-level deploy artifacts.
container-purge-system: container-purge-entity
	@bash scripts/tests/deploy/local/purge/inventory.sh
	@bash scripts/tests/deploy/local/purge/web.sh
	@bash scripts/tests/deploy/local/purge/lib.sh

# Create a fresh inventory and deploy all apps.
deploy-fresh-kept-all:
	@echo "=== local full deploy (type=$${INFINITO_TEST_DEPLOY_TYPE}, distro=$${INFINITO_DISTRO}) ==="
	@bash scripts/tests/deploy/local/deploy/fresh-kept-all.sh

# Create a fresh inventory and deploy one or more apps.
deploy-fresh-kept-apps:
	@: "$${INFINITO_APPS:?INFINITO_APPS must be set (e.g. INFINITO_APPS=web-app-nextcloud)}"
	@bash scripts/tests/deploy/local/deploy/fresh-kept-app.sh "$${INFINITO_APPS}"

# Deploy one or more apps with purged entities. Set INFINITO_FULL_CYCLE=true to also run the update pass.
deploy-fresh-purged-apps: down up
	@bash scripts/tests/deploy/local/deploy/fresh-purged-app.sh

# Redeploy one or more apps on an existing inventory.
deploy-reuse-kept-apps:
	@INFINITO_DEBUG=true bash scripts/tests/deploy/local/deploy/reuse-kept-app.sh

# Redeploy all apps on an existing inventory.
deploy-reuse-kept-all:
	@bash scripts/tests/deploy/local/deploy/reuse-kept-all.sh

# Purge one or more app entities, then redeploy them on existing inventory.
deploy-reuse-purged-apps: container-purge-entity
	@$(MAKE) deploy-reuse-kept-apps

# One-off deploy of all apps cumulated from one or more inventory bundles. Set INFINITO_FULL_CYCLE=true to also run the update pass (default: false).
deploy-bundles: down up
	@bash scripts/tests/deploy/local/deploy/bundles.sh

# Redeploy all apps cumulated from inventory bundles on an existing inventory (no down/up, no entity purge; requires a prior deploy-bundles run).
redeploy-bundles:
	@bash scripts/tests/deploy/local/deploy/redeploy-bundles.sh