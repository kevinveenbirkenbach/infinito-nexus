.ONESHELL:
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

# ------------------------------------------------------------
# SPOT: Global environment is defined in scripts/meta/env/all.sh
# ------------------------------------------------------------
ENV_SH ?= $(CURDIR)/scripts/meta/env/all.sh
export ENV_SH

# For non-interactive bash, BASH_ENV is sourced before executing the command.
# This makes the env layer apply automatically to *all* Make recipes.
ifneq ("$(wildcard $(ENV_SH))","")
export BASH_ENV := $(ENV_SH)
else
$(error Missing env file: $(ENV_SH))
endif

.PHONY: \
	setup setup-clean install install-ansible install-lint install-venv install-python install-system-python \
	test lint lint-action lint-ansible lint-python lint-shellcheck test-lint test-unit test-integration test-deploy test-deploy-app \
	clean clean-sudo down \
	list tree mig dockerignore \
	print-python \
	dns-setup dns-remove \
	dev-environment-bootstrap dev-environment-teardown \
	wsl2-systemd-check wsl2-dns-setup wsl2-trust-windows \
	apparmor-teardown apparmor-restore \
	disable-ipv6 restore-ipv6 \
	trust-ca \
	restart up down stop \
	build build-missing build-no-cache build-no-cache-all cleanup-ci-images \
	ci-deploy-app \
	test-act-all test-act-app test-act-workflow \
	test-local-app test-local-reset test-local-run-all test-local-cleanup test-local-web-purge \
	test-local-rapid test-local-rapid-fresh test-local-full \
	bootstrap setup-development

dev-environment-bootstrap: wsl2-systemd-check install-lint apparmor-teardown dns-setup disable-ipv6
dev-environment-teardown: apparmor-restore dns-remove restore-ipv6

wsl2-systemd-check:
	@bash scripts/administration/systemd/enable/wsl2.sh

wsl2-dns-setup:
	@sudo bash scripts/administration/network/dns/setup/wsl.sh

wsl2-trust-windows:
	@bash scripts/administration/tls/trust/wsl2.sh

dns-setup: wsl2-dns-setup
	@bash scripts/administration/network/dns/setup/linux.sh

dns-remove:
	@bash scripts/administration/network/dns/remove.sh

apparmor-teardown:
	@echo "==> AppArmor: full teardown (local dev)"
	@if grep -q '^[Yy1]' /sys/module/apparmor/parameters/enabled 2>/dev/null; then \
		sudo bash scripts/administration/apparmor/teardown.sh; \
	else \
		echo "[apparmor] AppArmor module is not loaded — skipping teardown"; \
	fi

apparmor-restore:
	@echo "==> AppArmor: restore profiles"
	@if grep -q '^[Yy1]' /sys/module/apparmor/parameters/enabled 2>/dev/null; then \
		sudo bash scripts/administration/apparmor/restore.sh; \
	else \
		echo "[apparmor] AppArmor module is not loaded — skipping restore"; \
	fi

trust-ca:
	@bash scripts/administration/tls/trust/linux.sh
	@bash scripts/administration/tls/trust/wsl2.sh

disable-ipv6:
	@sudo bash scripts/administration/network/ipv6/disable.sh

restore-ipv6:
	@sudo bash scripts/administration/network/ipv6/restore.sh

clean:
	@echo "Removing ignored git files"
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		git clean -fdX; \
	else \
		echo "WARNING: not inside a git repository -> skipping 'git clean -fdX'"; \
		echo "WARNING: (cleanup continues)"; \
	fi

clean-sudo:
	@echo "Removing ignored git files with sudo"
	sudo git clean -fdX;

restart:
	@"$${PYTHON}" -m cli.deploy.development restart --distro "$${INFINITO_DISTRO}"

up: install
	@"$${PYTHON}" -m cli.deploy.development up

down:
	@"$${PYTHON}" -m cli.deploy.development down

stop:
	@"$${PYTHON}" -m cli.deploy.development stop

list:
	@echo "Generating the roles list"
	@"$${PYTHON}" -m cli.build.roles_list

tree:
	@echo "Generating Tree"
	@"$${PYTHON}" -m cli.build.tree -D 2

mig: list tree
	@echo "Creating meta data for meta infinity graph"

# ------------------------------------------------------------
# Docker build targets (delegated to scripts/image)
# ------------------------------------------------------------
build: dockerignore
	@bash scripts/image/build.sh

build-missing:
	@bash scripts/image/build.sh --missing

build-dependency:
	@docker pull ghcr.io/kevinveenbirkenbach/pkgmgr-$${INFINITO_DISTRO}:stable

build-no-cache: build-dependency
	@bash scripts/image/build.sh --no-cache

build-no-cache-all:
	@set -euo pipefail; \
	for d in $${DISTROS}; do \
	  echo "=== build-no-cache: $$d ==="; \
	  INFINITO_DISTRO="$$d" "$(MAKE)" build-no-cache; \
	done

cleanup-ci-images:
	@bash scripts/image/cleanup.sh

dockerignore:
	@echo "Create dockerignore"
	cat .gitignore > .dockerignore
	echo ".git" >> .dockerignore

install-ansible:
	@ANSIBLE_COLLECTIONS_DIR="$(HOME)/.ansible/collections" \
	bash scripts/install/ansible.sh

install-lint:
	@bash scripts/install/lint.sh

install-system-python:
	@bash roles/dev-python/files/install.sh ensure

install-venv: install-system-python
	@bash scripts/install/venv.sh

install-python: install-venv
	@bash scripts/install/python.sh lint

install: install-python install-ansible

setup: dockerignore
	@bash scripts/setup.sh

setup-development: dockerignore
	touch env.development

bootstrap: install setup

setup-clean: clean setup
	@echo "Full build with cleanup before was executed."

# --- Lint ---
lint: lint-action lint-ansible lint-python lint-shellcheck

lint-action:
	@bash scripts/lint/action.sh

lint-ansible:
	@bash scripts/lint/ansible.sh

lint-python:
	@bash scripts/lint/python.sh

lint-shellcheck:
	@bash scripts/lint/shellcheck.sh

# --- Tests (separated) ---
test: lint test-lint test-unit test-integration test-deploy
	@echo "✅ Full test (setup + tests) executed."

test-lint: install
	@TEST_TYPE="lint" \
	INFINITO_COMPILE=0 \
	bash scripts/tests/code.sh

test-unit: install
	@TEST_TYPE="unit" \
	INFINITO_COMPILE=0 \
	bash scripts/tests/code.sh

test-integration: install
	@TEST_TYPE="integration" \
	INFINITO_COMPILE=0 \
	bash scripts/tests/code.sh

ci-deploy-app:
	@export MISSING_ONLY=true; \
	export MAX_TOTAL_SECONDS=19800; \
	./scripts/tests/deploy/ci/all_distros.sh

test-act-all:
	@bash scripts/tests/deploy/act/all.sh

test-act-app:
	@bash scripts/tests/deploy/act/app.sh

test-act-workflow:
	@bash scripts/tests/deploy/act/workflow.sh

test-local-app:
	@: "$${APP:?APP must be set (e.g. APP=web-app-nextcloud)}"
	@bash scripts/tests/deploy/local/app.sh "$${APP}"

test-local-reset:
	@bash scripts/tests/deploy/local/utils/reset.sh

test-local-run-all:
	@bash scripts/tests/deploy/local/run-all.sh

test-local-cleanup-entity:
	@bash scripts/tests/deploy/local/utils/purge/entity.sh

test-local-cleanup: test-local-cleanup-entity
	@bash scripts/tests/deploy/local/utils/purge/inventory.sh
	@bash scripts/tests/deploy/local/utils/purge/web.sh
	@bash scripts/tests/deploy/local/utils/purge/lib.sh

test-local-dedicated: down up
	@bash scripts/tests/deploy/local/dedicated_distro.sh

test-local-rapid:
	@DEBUG=true \
	bash scripts/tests/deploy/local/rapid.sh

test-local-rapid-fresh: test-local-cleanup-entity test-local-rapid

test-local-full:
	@echo "=== local full deploy (type=$${TEST_DEPLOY_TYPE}, distro=$${INFINITO_DISTRO}) ==="
	@bash scripts/tests/deploy/local/all.sh
