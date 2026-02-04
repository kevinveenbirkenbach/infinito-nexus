.ONESHELL:
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

# ------------------------------------------------------------
# SPOT: Global environment is defined in scripts/meta/env.sh
# ------------------------------------------------------------
ENV_SH ?= $(CURDIR)/scripts/meta/env.sh
export ENV_SH

# For non-interactive bash, BASH_ENV is sourced before executing the command.
# This makes env.sh apply automatically to *all* Make recipes.
ifneq ("$(wildcard $(ENV_SH))","")
export BASH_ENV := $(ENV_SH)
else
$(error Missing env file: $(ENV_SH))
endif

.PHONY: \
	setup setup-clean install install-ansible install-venv install-python \
	test test-lint test-unit test-integration test-deploy test-deploy-app \
	clean clean-sudo down \
	list tree mig dockerignore \
	print-python lint-ansible \
	dns-setup dns-remove \
	dev-environment-bootstrap dev-environment-teardown \
	apparmor-teardown apparmor-restore \
	trust-ca \
	docker-restart docker-up docker-down docker-stop \
	build build-missing build-no-cache build-no-cache-all \
	ci-deploy-discover ci-deploy-app ci-discover-output \
	test-act-all test-act-app \
	test-local-reset test-local-run-all test-local-cleanup test-local-web-purge \
	test-local-rapid test-local-rapid-fresh test-local-full \
	format bootstrap setup-development

dev-environment-bootstrap: apparmor-teardown dns-setup
dev-environment-teardown: apparmor-restore dns-remove

dns-setup:
	@bash scripts/dns/setup.sh

dns-remove:
	@bash scripts/dns/remove.sh

apparmor-teardown:
	@echo "==> AppArmor: full teardown (local dev)"
	@sudo bash scripts/administration/apparmor/teardown.sh

apparmor-restore:
	@echo "==> AppArmor: restore profiles"
	@sudo bash scripts/administration/apparmor/restore.sh

trust-ca:
	@bash scripts/administration/trust_ca.sh

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

docker-restart:
	@"$${PYTHON}" -m cli.deploy.development restart --distro "$${INFINITO_DISTRO}"

docker-up: install
	@"$${PYTHON}" -m cli.deploy.development up

docker-down:
	@"$${PYTHON}" -m cli.deploy.development down

docker-stop:
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
# Docker build targets (delegated to scripts/build)
# ------------------------------------------------------------
build:
	@bash scripts/build/image.sh

build-missing:
	@bash scripts/build/image.sh --missing

build-no-cache:
	@bash scripts/build/image.sh --no-cache

build-no-cache-all:
	@set -euo pipefail; \
	for d in $${DISTROS}; do \
	  echo "=== build-no-cache: $$d ==="; \
	  INFINITO_DISTRO="$$d" "$(MAKE)" build-no-cache; \
	done

dockerignore:
	@echo "Create dockerignore"
	cat .gitignore > .dockerignore
	echo ".git" >> .dockerignore

install-ansible:
	@ANSIBLE_COLLECTIONS_DIR="$(HOME)/.ansible/collections" \
	bash scripts/install/ansible.sh

install-venv:
	@bash scripts/install/venv.sh

install-python: install-venv
	@bash scripts/install/python.sh

install: install-python install-ansible

setup: dockerignore
	@bash scripts/setup.sh

setup-development: dockerignore
	touch env.development

bootstrap: install setup

setup-clean: clean setup
	@echo "Full build with cleanup before was executed."

format:
	set -euo pipefail; \
	shfmt -w scripts; \
	ruff format .; \
	ruff check . --fix

# --- Tests (separated) ---
test: test-lint test-unit test-integration lint-ansible test-deploy
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

ci-deploy-discover:
	@PYTHON=python3 ./scripts/meta/build-test-matrix.sh

ci-deploy-app:
	@export MISSING_ONLY=true; \
	export MAX_TOTAL_SECONDS=19800; \
	./scripts/tests/deploy/ci/all_distros.sh

ci-discover-output:
	@set -euo pipefail; \
	apps="$$(./scripts/meta/build-test-matrix.sh)"; \
	[[ -n "$$apps" ]] || apps='[]'; \
	if [[ -n "$${ONLY_APP:-}" ]]; then \
	  apps="$$(jq -nc --arg a "$$ONLY_APP" '[ $$a ]')"; \
	fi; \
	if [[ -n "$${GITHUB_OUTPUT:-}" ]]; then \
	  echo "apps=$$apps" >> "$$GITHUB_OUTPUT"; \
	  echo "apps_json=$$apps" >> "$$GITHUB_OUTPUT"; \
	fi; \
	echo "apps_json=$$apps"

test-act-all:
	@bash scripts/tests/deploy/act/all.sh

test-act-app:
	@bash scripts/tests/deploy/act/app.sh

test-local-reset:
	@PYTHON=python3 \
	bash scripts/tests/deploy/local/utils/reset.sh

test-local-run-all:
	@bash scripts/tests/deploy/local/run-all.sh

test-local-cleanup:
	@bash scripts/tests/deploy/local/utils/purge/inventory.sh
	@bash scripts/tests/deploy/local/utils/purge/entity.sh
	@bash scripts/tests/deploy/local/utils/purge/web.sh
	@bash scripts/tests/deploy/local/utils/purge/lib.sh

test-local-dedicated: test-local-cleanup
	@bash scripts/tests/deploy/local/dedicated_distro.sh

test-local-rapid:
	@DEBUG=true \
	bash scripts/tests/deploy/local/rapid.sh

test-local-rapid-fresh: test-local-cleanup test-local-rapid

test-local-full:
	@echo "=== local full deploy (type=$${TEST_DEPLOY_TYPE}, distro=$${INFINITO_DISTRO}) ==="
	@bash scripts/tests/deploy/local/all.sh

# Backwards compatible target (kept)
lint-ansible:
	@echo "📑 Checking Ansible syntax…"
	ansible-playbook -i localhost, -c local $(foreach f,$(wildcard group_vars/all/*.yml),-e @$(f)) playbook.yml --syntax-check
