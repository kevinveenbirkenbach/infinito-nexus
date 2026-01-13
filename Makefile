.ONESHELL:
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

# ------------------------------------------------------------
# Python / venv
#
# Rule:
#  - If a venv is already active (VIRTUAL_ENV), use it.
#  - Otherwise fall back to the global venv location.
# ------------------------------------------------------------
VENV_BASE ?= $(if $(VIRTUAL_ENV),$(dir $(VIRTUAL_ENV)),/opt/venvs)
VENV_NAME ?= infinito
VENV_FALLBACK := $(VENV_BASE)/$(VENV_NAME)

VENV := $(if $(VIRTUAL_ENV),$(VIRTUAL_ENV),$(VENV_FALLBACK))

PYTHON := $(VENV)/bin/python
PIP    := $(PYTHON) -m pip
export PYTHON
export PIP

# Nix Config Variable (To avoid rate limit)
NIX_CONFIG ?=
export NIX_CONFIG

ROLES_DIR           := ./roles
APPLICATIONS_OUT    := ./group_vars/all/04_applications.yml
APPLICATIONS_SCRIPT := ./cli/setup/applications/__main__.py
USERS_SCRIPT        := ./cli/setup/users/__main__.py
USERS_OUT           := ./group_vars/all/03_users.yml
INCLUDES_SCRIPT     := ./cli/build/role_include/__main__.py

# Directory where these include-files will be written
INCLUDES_OUT_DIR    := ./tasks/groups

# --- Test filtering (unittest discover) ---
TEST_PATTERN            ?= test*.py
export TEST_PATTERN
LINT_TESTS_DIR          ?= tests/lint
UNIT_TESTS_DIR          ?= tests/unit
INTEGRATION_TESTS_DIR   ?= tests/integration

# Deploy test type
# Allowed: server, workstation
TEST_DEPLOY_TYPE ?= server

# Ensure repo root is importable (so module_utils/, filter_plugins/ etc. work)
PYTHONPATH              ?= .

# Distro
INFINITO_DISTRO		?= arch
INFINITO_CONTAINER 	?= infinito_nexus_$(INFINITO_DISTRO)
export INFINITO_DISTRO
export INFINITO_CONTAINER

# Compute extra users as before
RESERVED_USERNAMES := $(shell \
  find $(ROLES_DIR) -maxdepth 1 -type d -printf '%f\n' \
    | sed -E 's/.*-//' \
    | grep -E -x '[a-z0-9]+' \
    | sort -u \
    | paste -sd, - \
)

.PHONY: \
	setup setup-clean install install-ansible install-venv install-python \
	test test-lint test-unit test-integration test-deploy test-deploy-app\
	clean down \
	list tree mig dockerignore \
	print-python lint-ansible

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

down:
	@echo ">>> Stopping infinito compose stack and removing volumes"
	@INFINITO_DISTRO="$(INFINITO_DISTRO)" docker compose --profile ci down --remove-orphans -v

up: build-missing
	@echo ">>> Start infinito compose stack (via python orchestrator)"
	@INFINITO_DISTRO="$(INFINITO_DISTRO)" python3 -m cli.deploy.test.up

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

# Global for all Infinito.Nexus environments used by the user
ANSIBLE_COLLECTIONS_DIR ?= $(HOME)/.ansible/collections

install-ansible:
	@echo "📦 Installing Ansible collections → $(ANSIBLE_COLLECTIONS_DIR)"
	@mkdir -p "$(ANSIBLE_COLLECTIONS_DIR)"
	@"$(PYTHON)" -m ansible.cli.galaxy collection install \
		-r requirements.yml \
		-p "$(ANSIBLE_COLLECTIONS_DIR)" \
		--force-with-deps

install-venv:
	@echo "✅ Python environment installed (editable)."
	@echo "🐍 Using venv: $(VENV)"
	@if [ -z "$(VIRTUAL_ENV)" ]; then \
		mkdir -p "$(VENV_BASE)"; \
	fi
	@if [ ! -x "$(PYTHON)" ]; then \
		echo "→ Creating virtualenv $(VENV)"; \
		python3 -m venv "$(VENV)"; \
	fi

install-python: install-venv
	@echo "📦 Installing Python dependencies"
	@"$(PYTHON)" -m pip install --upgrade pip setuptools wheel
	@"$(PYTHON)" -m pip install -e .

install: install-python install-ansible

setup: dockerignore
	@echo "🔧 Generating users defaults → $(USERS_OUT)…"
	$(PYTHON) $(USERS_SCRIPT) \
	  --roles-dir $(ROLES_DIR) \
	  --output $(USERS_OUT) \
	  --reserved-usernames "$(RESERVED_USERNAMES)"
	@echo "✅ Users defaults written to $(USERS_OUT)\n"

	@echo "🔧 Generating applications defaults → $(APPLICATIONS_OUT)…"
	$(PYTHON) $(APPLICATIONS_SCRIPT) \
	  --roles-dir $(ROLES_DIR) \
	  --output-file $(APPLICATIONS_OUT)
	@echo "✅ Applications defaults written to $(APPLICATIONS_OUT)\n"

	@echo "🔧 Generating role-include files for each group…"
	@mkdir -p $(INCLUDES_OUT_DIR)
	@INCLUDE_GROUPS="$$( $(PYTHON) -m cli.meta.categories.invokable -s "-" | tr '\n' ' ' )"; \
	for grp in $$INCLUDE_GROUPS; do \
	  out="$(INCLUDES_OUT_DIR)/$${grp}roles.yml"; \
	  echo "→ Building $$out (pattern: '$$grp')…"; \
	  $(PYTHON) $(INCLUDES_SCRIPT) $(ROLES_DIR) -p $$grp -o $$out; \
	  echo "  ✅ $$out"; \
	done

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

test-lint: build-missing
	@TEST_TYPE="lint" bash scripts/tests/code.sh

test-unit: build-missing
	@TEST_TYPE="unit" bash scripts/tests/code.sh

test-integration: build-missing
	@TEST_TYPE="integration" bash scripts/tests/code.sh

# ------------------------------------------------------------
# Deploy test for a single app (serial, fail-fast)
# Controlled by:
#   TEST_DEPLOY_TYPE (server|workstation|rest)
#   INFINITO_DISTRO  (arch|debian|ubuntu|fedora|centos)
# Usage:
#   make test-deploy-app APP=web-app-nextcloud
#   make test-deploy-app TEST_DEPLOY_TYPE=workstation INFINITO_DISTRO=debian APP=desk-kde
# ------------------------------------------------------------
test-deploy-app: build-missing up
	@if [[ -z "$(APP)" ]]; then \
	  echo "ERROR: APP is not set"; \
	  echo "Usage: make test-deploy-app APP=web-app-nextcloud"; \
	  exit 1; \
	fi; \
	case "$(TEST_DEPLOY_TYPE)" in \
	  server|workstation|rest) ;; \
	  *) echo "ERROR: invalid TEST_DEPLOY_TYPE=$(TEST_DEPLOY_TYPE) (server|workstation|rest)"; exit 2 ;; \
	esac; \
	echo "=== act: workflow_dispatch deploy:$(TEST_DEPLOY_TYPE) app=$(APP) distro=$(INFINITO_DISTRO) ==="; \
	act workflow_dispatch \
		-W .github/workflows/_deploy-matrix.yml \
		--input mode:"$(TEST_DEPLOY_TYPE)" \
		--input only_app:"$(APP)" \
		--input only_distro:"$(INFINITO_DISTRO)" \
		--privileged \
		--network host \
		--concurrent-jobs 1


# ------------------------------------------------------------
# Deploy test for all discovered apps (calls test-deploy-app)
# Controlled by:
#   TEST_DEPLOY_TYPE (server|workstation|rest)
#   INFINITO_DISTRO  (single distro for local run)
# ------------------------------------------------------------
test-deploy: build-missing up
	@set -euo pipefail; \
	case "$(TEST_DEPLOY_TYPE)" in \
	  server) \
	    include_re='^(web-app-|web-svc-)'; \
	    exclude_re='^(web-app-oauth2-proxy)$$'; \
	    ;; \
	  workstation) \
	    include_re='^(desk-|util-desk-)'; \
	    exclude_re=''; \
	    ;; \
	  rest) \
	    include_re='.*'; \
	    exclude_re=''; \
	    ;; \
	  *) \
	    echo "ERROR: invalid TEST_DEPLOY_TYPE=$(TEST_DEPLOY_TYPE) (server|workstation|rest)"; \
	    exit 2; \
	    ;; \
	esac; \
	echo "=== Discover apps (JSON) type=$(TEST_DEPLOY_TYPE) distro=$(INFINITO_DISTRO) ==="; \
	export INFINITO_DISTRO="$(INFINITO_DISTRO)"; \
	apps_json="$$(INCLUDE_RE="$${include_re}" EXCLUDE_RE="$${exclude_re}" scripts/tests/discover-apps.sh)"; \
	if [[ -z "$$apps_json" ]]; then apps_json="[]"; fi; \
	echo "$$apps_json" | jq -e . >/dev/null; \
	echo "Apps: $$apps_json"; \
	echo; \
	for app in $$(echo "$$apps_json" | jq -r '.[]'); do \
		$(MAKE) test-deploy-app APP="$$app" TEST_DEPLOY_TYPE="$(TEST_DEPLOY_TYPE)" INFINITO_DISTRO="$(INFINITO_DISTRO)"; \
		echo; \
	done

# Backwards compatible target (kept)
lint-ansible:
	@echo "📑 Checking Ansible syntax…"
	ansible-playbook -i localhost, -c local $(foreach f,$(wildcard group_vars/all/*.yml),-e @$(f)) playbook.yml --syntax-check

# Debug helper
print-python:
	@echo "VENV_BASE       = $(VENV_BASE)"
	@echo "VENV_NAME       = $(VENV_NAME)"
	@echo "VENV            = $(VENV)"
	@echo "Selected PYTHON = $(PYTHON)"
	@$(PYTHON) -c 'import sys; print("sys.executable =", sys.executable); print("sys.prefix     =", sys.prefix); print("sys.base_prefix=", sys.base_prefix); print("is_venv        =", sys.prefix != sys.base_prefix)'
