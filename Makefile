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
	test test-lint test-unit test-integration test-deploy \
	clean clean-container \
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

clean-container:
	@echo ">>> Stopping infinito compose stack and removing volumes"
	@INFINITO_DISTRO="$(INFINITO_DISTRO)" docker compose --profile ci down --remove-orphans -v

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

ANSIBLE_COLLECTIONS_DIR ?= ./collections

install-ansible:
	@echo "📦 Installing Ansible collections from requirements.yml → $(ANSIBLE_COLLECTIONS_DIR)"
	@mkdir -p "$(ANSIBLE_COLLECTIONS_DIR)"
	@"$(PYTHON)" -m ansible.cli.galaxy collection install \
		-r requirements.yml \
		-p "$(ANSIBLE_COLLECTIONS_DIR)"

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

test-lint: build-missing
	@TEST_TYPE="lint" bash scripts/tests/code.sh

test-unit: build-missing
	@TEST_TYPE="unit" bash scripts/tests/code.sh

test-integration: build-missing
	@TEST_TYPE="integration" bash scripts/tests/code.sh

test-deploy:
	@INFINITO_DISTRO="$(INFINITO_DISTRO)" \
	INFINITO_CONTAINER="$(INFINITO_CONTAINER)" \
	scripts/tests/deploy.sh \
	  --type "$(TEST_DEPLOY_TYPE)" \
	  --missing

# Backwards compatible target (kept)
lint-ansible:
	@echo "📑 Checking Ansible syntax…"
	ansible-playbook -i localhost, -c local $(foreach f,$(wildcard group_vars/all/*.yml),-e @$(f)) playbook.yml --syntax-check

test: test-lint test-unit test-integration lint-ansible test-deploy
	@echo "✅ Full test (setup + tests) executed."

# Debug helper
print-python:
	@echo "VENV_BASE       = $(VENV_BASE)"
	@echo "VENV_NAME       = $(VENV_NAME)"
	@echo "VENV            = $(VENV)"
	@echo "Selected PYTHON = $(PYTHON)"
	@$(PYTHON) -c 'import sys; print("sys.executable =", sys.executable); print("sys.prefix     =", sys.prefix); print("sys.base_prefix=", sys.base_prefix); print("is_venv        =", sys.prefix != sys.base_prefix)'
