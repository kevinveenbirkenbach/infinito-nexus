ROLES_DIR           := ./roles
APPLICATIONS_OUT    := ./group_vars/all/04_applications.yml
APPLICATIONS_SCRIPT := ./cli/build/defaults/applications.py
USERS_OUT           := ./group_vars/all/03_users.yml
USERS_SCRIPT        := ./cli/build/defaults/users.py
INCLUDES_SCRIPT     := ./cli/build/role_include.py
PYTHON  			?= python3

INCLUDE_GROUPS = $(shell $(PYTHON) main.py meta categories invokable -s "-" --no-signal | tr '\n' ' ')

# Directory where these include-files will be written
INCLUDES_OUT_DIR    := ./tasks/groups

# Compute extra users as before
RESERVED_USERNAMES := $(shell \
  find $(ROLES_DIR) -maxdepth 1 -type d -printf '%f\n' \
    | sed -E 's/.*-//' \
    | grep -E -x '[a-z0-9]+' \
    | sort -u \
    | paste -sd, - \
)

.PHONY: build install test

clean-keep-logs:
	@echo "🧹 Cleaning ignored files but keeping logs/…"
	git clean -fdX -- ':!logs' ':!logs/**'

clean:
	@echo "Removing ignored git files"
	git clean -fdX

list:
	@echo Generating the roles list
	$(PYTHON) main.py build roles_list

tree:
	@echo Generating Tree
	$(PYTHON) main.py build tree -D 2 --no-signal

mig: list tree
	@echo Creating meta data for meta infinity graph

dockerignore:
	@echo Create dockerignore
	cat .gitignore > .dockerignore
	echo ".git" >> .dockerignore 

messy-build: dockerignore
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
	@$(foreach grp,$(INCLUDE_GROUPS), \
	  out=$(INCLUDES_OUT_DIR)/$(grp)roles.yml; \
	  echo "→ Building $$out (pattern: '$(grp)')…"; \
	  $(PYTHON) $(INCLUDES_SCRIPT) $(ROLES_DIR) \
	    -p $(grp) -o $$out; \
	  echo "  ✅ $$out"; \
	)

messy-test: 
	@echo "🧪 Running Python tests…"
	PYTHONPATH=. $(PYTHON) -m unittest discover -s tests
	@echo "📑 Checking Ansible syntax…"
	ansible-playbook -i localhost, -c local $(foreach f,$(wildcard group_vars/all/*.yml),-e @$(f)) playbook.yml --syntax-check

install: build
	@echo "⚙️  Install complete."

build: clean messy-build
	@echo "Full build with cleanup before was executed."

test: build messy-test
	@echo "Full test with build before was executed."
