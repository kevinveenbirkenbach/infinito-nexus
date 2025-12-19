SHELL 				:= /usr/bin/env bash

# ------------------------------------------------------------
# Python / venv (GLOBAL, NOT inside project)
#
# Goal:
#  - Never create a venv inside the project folder.
#  - Use a stable venv location and export PYTHON so subprocesses can reuse it.
#
# Defaults work well inside the Docker image.
# On a local host you may want to override:
#   make VENV_BASE=$$HOME/.venvs install
# ------------------------------------------------------------
VENV_BASE           ?= /opt/venvs
VENV_NAME           ?= infinito
VENV                := $(VENV_BASE)/$(VENV_NAME)

PYTHON              := $(VENV)/bin/python
PIP                 := $(PYTHON) -m pip

export PYTHON
export PIP

ROLES_DIR           := ./roles
APPLICATIONS_OUT    := ./group_vars/all/04_applications.yml
APPLICATIONS_SCRIPT := ./cli/setup/applications.py
USERS_SCRIPT        := ./cli/setup/users.py
USERS_OUT           := ./group_vars/all/03_users.yml
INCLUDES_SCRIPT     := ./cli/build/role_include.py

# Directory where these include-files will be written
INCLUDES_OUT_DIR    := ./tasks/groups

# --- Test filtering (unittest discover) ---
TEST_PATTERN            ?= test*.py
export TEST_PATTERN
LINT_TESTS_DIR          ?= tests/lint
UNIT_TESTS_DIR          ?= tests/unit
INTEGRATION_TESTS_DIR   ?= tests/integration

# Ensure repo root is importable (so module_utils/, filter_plugins/ etc. work)
PYTHONPATH              ?= .

# Distro
INFINITO_DISTRO		?= arch
export INFINITO_DISTRO

# Compute extra users as before
RESERVED_USERNAMES := $(shell \
  find $(ROLES_DIR) -maxdepth 1 -type d -printf '%f\n' \
    | sed -E 's/.*-//' \
    | grep -E -x '[a-z0-9]+' \
    | sort -u \
    | paste -sd, - \
)

.PHONY: \
	deps setup setup-clean install \
	test test-messy test-lint test-unit test-integration \
	clean list tree mig dockerignore \
	print-python

clean:
	@echo "Removing ignored git files"
	@git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { \
		echo "Error: not inside a git repository"; \
		exit 1; \
	}
	git clean -fdX

list:
	@echo "Generating the roles list"
	$(PYTHON) -m cli build roles_list

tree:
	@echo "Generating Tree"
	$(PYTHON) -m cli build tree -D 2 --no-signal

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

# ------------------------------------------------------------
# Install (GLOBAL venv, never in project folder)
# ------------------------------------------------------------
install: deps
	@echo "✅ Python environment installed (editable)."
	@echo "🐍 Using global venv: $(VENV)"
	@mkdir -p "$(VENV_BASE)"
	@if [ ! -x "$(PYTHON)" ]; then \
		echo "→ Creating virtualenv $(VENV)"; \
		python3 -m venv "$(VENV)"; \
	fi
	@echo "📦 Installing Python dependencies"
	@"$(PYTHON)" -m pip install --upgrade pip setuptools wheel
	@"$(PYTHON)" -m pip install -e .

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
	@INCLUDE_GROUPS="$$( $(PYTHON) -m cli meta categories invokable -s "-" --no-signal | tr '\n' ' ' )"; \
	for grp in $$INCLUDE_GROUPS; do \
	  out="$(INCLUDES_OUT_DIR)/$${grp}roles.yml"; \
	  echo "→ Building $$out (pattern: '$$grp')…"; \
	  $(PYTHON) $(INCLUDES_SCRIPT) $(ROLES_DIR) -p $$grp -o $$out; \
	  echo "  ✅ $$out"; \
	done

setup-clean: clean setup
	@echo "Full build with cleanup before was executed."

# --- Tests (separated) ---

test-lint: build-missing
	@TEST_TYPE="lint" bash scripts/tests/code.sh

test-unit: build-missing
	@TEST_TYPE="unit" bash scripts/tests/code.sh

test-integration: build-missing
	@TEST_TYPE="integration" bash scripts/tests/code.sh

# Backwards compatible target (kept)
lint-ansible:
	@echo "📑 Checking Ansible syntax…"
	ansible-playbook -i localhost, -c local $(foreach f,$(wildcard group_vars/all/*.yml),-e @$(f)) playbook.yml --syntax-check

test: test-lint test-unit test-integration test-ansible
	@echo "✅ Full test (setup + tests) executed."

# Debug helper
print-python:
	@echo "VENV_BASE       = $(VENV_BASE)"
	@echo "VENV_NAME       = $(VENV_NAME)"
	@echo "VENV            = $(VENV)"
	@echo "Selected PYTHON = $(PYTHON)"
	@$(PYTHON) -c 'import sys; print("sys.executable =", sys.executable); print("sys.prefix     =", sys.prefix); print("sys.base_prefix=", sys.base_prefix); print("is_venv        =", sys.prefix != sys.base_prefix)'
