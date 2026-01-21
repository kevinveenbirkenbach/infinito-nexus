.ONESHELL:
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

VENV_BASE ?= $(if $(VIRTUAL_ENV),$(dir $(VIRTUAL_ENV)),/opt/venvs)
VENV_NAME ?= infinito
VENV_FALLBACK := $(VENV_BASE)/$(VENV_NAME)
VENV := $(if $(VIRTUAL_ENV),$(VIRTUAL_ENV),$(VENV_FALLBACK))

PYTHON := $(VENV)/bin/python
PIP    := $(PYTHON) -m pip
export PYTHON
export PIP

# Ensure repo root is importable (so module_utils/, filter_plugins/ etc. work)
PYTHONPATH ?= .
export PYTHONPATH

ifdef NIX_CONFIG
export NIX_CONFIG
endif

# Ensure TEST_DEPLOY_TYPE is available for the default inventory dir.
TEST_DEPLOY_TYPE ?= server
export TEST_DEPLOY_TYPE

# --- Test filtering (unittest discover) ---
TEST_PATTERN            ?= test*.py
export TEST_PATTERN

# Distro
INFINITO_DISTRO		?= arch
INFINITO_CONTAINER 	?= infinito_nexus_$(INFINITO_DISTRO)
export INFINITO_DISTRO
export INFINITO_CONTAINER

# Detirmene Environment 
RUNNING_ON_ACT    ?= false
RUNNING_ON_GITHUB ?= false

ifeq ($(GITHUB_ACTIONS),true)
	RUNNING_ON_GITHUB = true
	ifeq ($(ACT),true)
		RUNNING_ON_ACT    = true
		RUNNING_ON_GITHUB = false
	endif
endif
export RUNNING_ON_ACT RUNNING_ON_GITHUB

INVENTORY_DIR ?= $(shell \
  RUNNING_ON_ACT="$(RUNNING_ON_ACT)" \
  RUNNING_ON_GITHUB="$(RUNNING_ON_GITHUB)" \
  HOME="$(HOME)" \
  bash scripts/inventory/resolve.sh \
)
export INVENTORY_DIR

# Overwrite defaults
ifeq ($(RUNNING_ON_GITHUB),true)
	# -------- Real GitHub Actions CI --------
	INFINITO_PULL_POLICY ?= always
	INFINITO_IMAGE_TAG ?= latest
	INFINITO_IMAGE ?= ghcr.io/$(GITHUB_REPOSITORY_OWNER)/infinito-$(INFINITO_DISTRO):$(INFINITO_IMAGE_TAG)
	INFINITO_NO_BUILD ?= 1
	INFINITO_DOCKER_VOLUME ?= /mnt/docker
	INFINITO_DOCKER_MOUNT ?= /var/lib/docker
	export INFINITO_DOCKER_VOLUME INFINITO_DOCKER_MOUNT
	export INFINITO_IMAGE_TAG
	export INFINITO_NO_BUILD
	export INFINITO_PULL_POLICY
	export INFINITO_IMAGE
	INFINITO_COMPILE ?=  0
else
	INFINITO_COMPILE ?= 1
endif
export INFINITO_COMPILE

.PHONY: \
	setup setup-clean install install-ansible install-venv install-python \
	test test-lint test-unit test-integration test-deploy test-deploy-app\
	clean down \
	list tree mig dockerignore \
	print-python lint-ansible \
	setup-dns remove-dns

setup-dns:
	@bash scripts/dns/setup.sh

remove-dns:
	@bash scripts/dns/remove.sh


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
	sudo git clean -fdX; \

docker-restart:
	@$(PYTHON) -m cli.deploy.development restart --distro "$(INFINITO_DISTRO)"

docker-up: install
	@$(PYTHON) -m cli.deploy.development up

docker-down:
	@$(PYTHON) -m cli.deploy.development down

docker-stop:
	@$(PYTHON) -m cli.deploy.development stop

list:
	@echo "Generating the roles list"
	$(PYTHON) -m cli.build.roles_list

tree:
	@echo "Generating Tree"
	$(PYTHON) -m cli.build.tree -D 2

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
	@set -e; \
	for d in $(DISTROS); do \
	  echo "=== build-no-cache: $$d ==="; \
	  INFINITO_DISTRO="$$d" $(MAKE) build-no-cache; \
	done

dockerignore:
	@echo "Create dockerignore"
	cat .gitignore > .dockerignore
	echo ".git" >> .dockerignore

install-ansible:
	@ANSIBLE_COLLECTIONS_DIR="$(HOME)/.ansible/collections" \
	PYTHON="$(PYTHON)" \
	bash scripts/install/ansible.sh

install-venv:
	@VENV="$(VENV)" \
	VENV_BASE="$(VENV_BASE)" \
	PYTHON="$(PYTHON)" \
	bash scripts/install/venv.sh

install-python: install-venv
	@bash scripts/install/python.sh

install: install-python install-ansible

setup: dockerignore
	@bash scripts/setup.sh

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
	export MISSING_ONLY=true; \
	./scripts/tests/deploy/ci/app.sh

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

test-act:
	@TEST_DEPLOY_TYPE="$(TEST_DEPLOY_TYPE)" \
	INFINITO_DISTRO="$(INFINITO_DISTRO)" \
	bash scripts/tests/deploy/act/all.sh

test-act-app:
	@APP="$(APP)" \
	TEST_DEPLOY_TYPE="$(TEST_DEPLOY_TYPE)" \
	INFINITO_DISTRO="$(INFINITO_DISTRO)" \
	bash scripts/tests/deploy/act/app.sh

test-local-inventory-init-all:
	@TEST_DEPLOY_TYPE="$(TEST_DEPLOY_TYPE)" \
	INFINITO_DISTRO="$(INFINITO_DISTRO)" \
	bash scripts/tests/deploy/local/inventory-init-all.sh

test-local-run-all:
	@TEST_DEPLOY_TYPE="$(TEST_DEPLOY_TYPE)" \
	INFINITO_DISTRO="$(INFINITO_DISTRO)" \
	DEBUG="$(DEBUG)" \
	LIMIT_HOST="$(LIMIT_HOST)" \
	INVENTORY_DIR="$(INVENTORY_DIR)" \
	bash scripts/tests/deploy/local/run-all.sh

test-local-cleanup:
	@APP="$(APP)" \
	INFINITO_CONTAINER="$(INFINITO_CONTAINER)" \
	bash scripts/tests/deploy/local/cleanup.sh

test-local-rapid:
	@APP="$(APP)" \
	TEST_DEPLOY_TYPE="$(TEST_DEPLOY_TYPE)" \
	INFINITO_CONTAINER="$(INFINITO_CONTAINER)" \
	DEBUG=true \
	bash scripts/tests/deploy/local/rapid.sh

test-local-rapid-fresh: test-local-cleanup test-local-rapid

test-local-full:
	@echo "=== local full deploy (type=$(TEST_DEPLOY_TYPE), distro=$(INFINITO_DISTRO)) ==="
	@TEST_DEPLOY_TYPE="$(TEST_DEPLOY_TYPE)" \
	INFINITO_DISTRO="$(INFINITO_DISTRO)" \
	bash scripts/tests/deploy/local/all.sh

# Backwards compatible target (kept)
lint-ansible:
	@echo "📑 Checking Ansible syntax…"
	ansible-playbook -i localhost, -c local $(foreach f,$(wildcard group_vars/all/*.yml),-e @$(f)) playbook.yml --syntax-check
