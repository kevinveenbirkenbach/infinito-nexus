SHELL 				:= /usr/bin/env bash

# ------------------------------------------------------------
# Python / venv selection (runtime-evaluated!)
#
# Priority:
#  1) Use local project venv if present: ./$(VENV)/bin/python
#  2) Else use the currently active shell python (via `command -v python`)
#     BUT only if that python is running inside a venv
#  3) Else fallback to the pkgmgr venv python (if it exists)
#  4) Else fallback to whatever `python` is on PATH (last resort)
#
# NOTE:
# Use recursive variables (=) so that after `.venv` is created during `make install`,
# subsequent lines will pick it up.
# ------------------------------------------------------------
VENV                ?= .venv
FALLBACK_PYTHON     ?= /home/kevinveenbirkenbach/.venvs/pkgmgr/bin/python

PYTHON = $(shell \
  if [ -x "$(VENV)/bin/python" ]; then \
    echo "$(VENV)/bin/python"; \
    exit 0; \
  fi; \
  py="$$(command -v python 2>/dev/null || true)"; \
  if [ -n "$$py" ]; then \
    is_venv="$$( "$$py" -c 'import sys; print("1" if sys.prefix != sys.base_prefix else "0")' 2>/dev/null || echo 0 )"; \
    if [ "$$is_venv" = "1" ]; then \
      echo "$$py"; \
      exit 0; \
    fi; \
  fi; \
  if [ -x "$(FALLBACK_PYTHON)" ]; then \
    echo "$(FALLBACK_PYTHON)"; \
  else \
    echo "$$py"; \
  fi \
)

PIP = $(PYTHON) -m pip

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
LINT_TESTS_DIR          ?= tests/lint
UNIT_TESTS_DIR          ?= tests/unit
INTEGRATION_TESTS_DIR   ?= tests/integration

# Ensure repo root is importable (so module_utils/, filter_plugins/ etc. work)
PYTHONPATH              ?= .

# Distro
INFINITO_DISTRO		?= arch
PKGMGR_DISTRO		= $(INFINITO_DISTRO)
export PKGMGR_DISTRO

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
	clean clean-keep-logs list tree mig dockerignore \
	print-python

clean-keep-logs:
	@echo "🧹 Cleaning ignored files but keeping logs/…"
	git clean -fdX -- ':!logs' ':!logs/**'

clean:
	@echo "Removing ignored git files"
	git clean -fdX

list:
	@echo "Generating the roles list"
	$(PYTHON) main.py build roles_list

tree:
	@echo "Generating Tree"
	$(PYTHON) main.py build tree -D 2 --no-signal

mig: list tree
	@echo "Creating meta data for meta infinity graph"

make build:
	docker build --network=host -t infinito:latest .

dockerignore:
	@echo "Create dockerignore"
	cat .gitignore > .dockerignore
	echo ".git" >> .dockerignore

install: deps
	@echo "✅ Python environment installed (editable)."
	@if [ ! -d "$(VENV)" ]; then \
			echo "🐍 Creating virtualenv $(VENV)"; \
			python3 -m venv "$(VENV)"; \
	fi
	@echo "📦 Installing Python dependencies"
	@"$(VENV)/bin/python" -m pip install --upgrade pip setuptools wheel
	@"$(VENV)/bin/python" -m pip install -e .

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
	@INCLUDE_GROUPS="$$( $(PYTHON) main.py meta categories invokable -s "-" --no-signal | tr '\n' ' ' )"; \
	for grp in $$INCLUDE_GROUPS; do \
	  out="$(INCLUDES_OUT_DIR)/$${grp}roles.yml"; \
	  echo "→ Building $$out (pattern: '$$grp')…"; \
	  $(PYTHON) $(INCLUDES_SCRIPT) $(ROLES_DIR) -p $$grp -o $$out; \
	  echo "  ✅ $$out"; \
	done

setup-clean: clean setup
	@echo "Full build with cleanup before was executed."

# --- Tests (separated) ---

test-lint:
	@if [ ! -d "$(LINT_TESTS_DIR)" ]; then \
		echo "ℹ️  No lint tests directory found at $(LINT_TESTS_DIR) (skipping)."; \
		exit 0; \
	fi
	@echo "🔎 Running lint tests (dir: $(LINT_TESTS_DIR), pattern: $(TEST_PATTERN))…"
	@PYTHONPATH="$(PYTHONPATH)" $(PYTHON) -m unittest discover \
		-s "$(LINT_TESTS_DIR)" \
		-p "$(TEST_PATTERN)" \
		-t "$(PYTHONPATH)"

test-unit:
	@if [ ! -d "$(UNIT_TESTS_DIR)" ]; then \
		echo "ℹ️  No unit tests directory found at $(UNIT_TESTS_DIR) (skipping)."; \
		exit 0; \
	fi
	@echo "🧪 Running unit tests (dir: $(UNIT_TESTS_DIR), pattern: $(TEST_PATTERN))…"
	@PYTHONPATH="$(PYTHONPATH)" $(PYTHON) -m unittest discover \
		-s "$(UNIT_TESTS_DIR)" \
		-p "$(TEST_PATTERN)" \
		-t "$(PYTHONPATH)"

test-integration:
	@if [ ! -d "$(INTEGRATION_TESTS_DIR)" ]; then \
		echo "ℹ️  No integration tests directory found at $(INTEGRATION_TESTS_DIR) (skipping)."; \
		exit 0; \
	fi
	@echo "🧪 Running integration tests (dir: $(INTEGRATION_TESTS_DIR), pattern: $(TEST_PATTERN))…"
	@PYTHONPATH="$(PYTHONPATH)" $(PYTHON) -m unittest discover \
		-s "$(INTEGRATION_TESTS_DIR)" \
		-p "$(TEST_PATTERN)" \
		-t "$(PYTHONPATH)"

# Backwards compatible target (kept)
test-messy: test-lint test-unit test-integration
	@echo "📑 Checking Ansible syntax…"
	ansible-playbook -i localhost, -c local $(foreach f,$(wildcard group_vars/all/*.yml),-e @$(f)) playbook.yml --syntax-check

test: clean setup test-messy
	@echo "✅ Full test (setup + tests) executed."

# Debug helper
print-python:
	@echo "Selected PYTHON = $(PYTHON)"
	@$(PYTHON) -c 'import sys; print("sys.executable =", sys.executable); print("sys.prefix     =", sys.prefix); print("sys.base_prefix=", sys.base_prefix); print("is_venv        =", sys.prefix != sys.base_prefix)'
