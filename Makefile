# ------------------------------------------------------------
# Multi-distro Docker build configuration (similar to pkgmgr)
# ------------------------------------------------------------
DISTROS           := arch debian ubuntu fedora centos
BASE_IMAGE_ARCH   := archlinux:latest
BASE_IMAGE_DEBIAN := debian:stable-slim
BASE_IMAGE_UBUNTU := ubuntu:latest
BASE_IMAGE_FEDORA := fedora:latest
BASE_IMAGE_CENTOS := quay.io/centos/centos:stream9

# Make them available to scripts (if you later add resolve-base-image.sh, etc.)
export DISTROS
export BASE_IMAGE_ARCH
export BASE_IMAGE_DEBIAN
export BASE_IMAGE_UBUNTU
export BASE_IMAGE_FEDORA
export BASE_IMAGE_CENTOS

# ------------------------------------------------------------
# Infinito roles/config generation
# ------------------------------------------------------------
ROLES_DIR           := ./roles
APPLICATIONS_OUT    := ./group_vars/all/04_applications.yml
APPLICATIONS_SCRIPT := ./cli/build/defaults/applications.py
USERS_OUT           := ./group_vars/all/03_users.yml
USERS_SCRIPT        := ./cli/build/defaults/users.py
INCLUDES_SCRIPT     := ./cli/build/role_include.py

INCLUDE_GROUPS := $(shell python3 main.py meta categories invokable -s "-" --no-signal | tr '\n' ' ')

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

.PHONY: build install test clean clean-keep-logs list tree mig dockerignore \
        messy-build messy-test \
        docker-build docker-build-no-cache

# ------------------------------------------------------------
# Core project targets
# ------------------------------------------------------------
clean-keep-logs:
	@echo "🧹 Cleaning ignored files but keeping logs/…"
	git clean -fdX -- ':!logs' ':!logs/**'

clean:
	@echo "🧹 Removing ignored git files…"
	git clean -fdX

list:
	@echo "📦 Generating the roles list…"
	python3 main.py build roles_list

tree:
	@echo "🌳 Generating roles tree…"
	python3 main.py build tree -D 2 --no-signal

mig: list tree
	@echo "🔗 Creating meta data for meta infinity graph…"

dockerignore:
	@echo "📝 Creating .dockerignore from .gitignore…"
	cat .gitignore > .dockerignore
	echo ".git" >> .dockerignore

messy-build: dockerignore
	@echo "🔧 Generating users defaults → $(USERS_OUT)…"
	python3 $(USERS_SCRIPT) \
	  --roles-dir $(ROLES_DIR) \
	  --output $(USERS_OUT) \
	  --reserved-usernames "$(RESERVED_USERNAMES)"
	@echo "✅ Users defaults written to $(USERS_OUT)\n"

	@echo "🔧 Generating applications defaults → $(APPLICATIONS_OUT)…"
	python3 $(APPLICATIONS_SCRIPT) \
	  --roles-dir $(ROLES_DIR) \
	  --output-file $(APPLICATIONS_OUT)
	@echo "✅ Applications defaults written to $(APPLICATIONS_OUT)\n"

	@echo "🔧 Generating role-include files for each group…"
	@mkdir -p $(INCLUDES_OUT_DIR)
	@$(foreach grp,$(INCLUDE_GROUPS), \
	  out=$(INCLUDES_OUT_DIR)/$(grp)roles.yml; \
	  echo "→ Building $$out (pattern: '$(grp)')…"; \
	  python3 $(INCLUDES_SCRIPT) $(ROLES_DIR) \
	    -p $(grp) -o $$out; \
	  echo "  ✅ $$out"; \
	)

messy-test:
	@echo "🧪 Running Python tests…"
	PYTHONPATH=. python -m unittest discover -s tests
	@echo "📑 Checking Ansible syntax…"
	ansible-playbook -i localhost, -c local $(foreach f,$(wildcard group_vars/all/*.yml),-e @$(f)) playbook.yml --syntax-check

install: build
	@echo "⚙️  Install complete."

build: clean messy-build
	@echo "✅ Full build (with cleanup) finished."

test: build messy-test
	@echo "✅ Full test (with build) finished."

# ------------------------------------------------------------
# Docker: multi-distro dev containers for Infinito
# Uses the multi-distro Dockerfile with ARG BASE_IMAGE
# ------------------------------------------------------------

# Helper to map distro → BASE_IMAGE_* variable
define _infinito_base_image
$(if $(filter $(1),arch),$(BASE_IMAGE_ARCH),\
$(if $(filter $(1),debian),$(BASE_IMAGE_DEBIAN),\
$(if $(filter $(1),ubuntu),$(BASE_IMAGE_UBUNTU),\
$(if $(filter $(1),fedora),$(BASE_IMAGE_FEDORA),\
$(if $(filter $(1),centos),$(BASE_IMAGE_CENTOS),)))))
endef

docker-build:
	@echo "============================================================"
	@echo ">>> Building Infinito dev containers for: $(DISTROS)"
	@echo "============================================================"
	@for distro in $(DISTROS); do \
	  base_image="$(call _infinito_base_image,$$distro)"; \
	  image_name="infinito-dev-$$distro"; \
	  echo; \
	  echo "------------------------------------------------------------"; \
	  echo ">>> Building $$image_name (BASE_IMAGE=$$base_image)…"; \
	  echo "------------------------------------------------------------"; \
	  docker build \
	    --build-arg BASE_IMAGE="$$base_image" \
	    -t "$$image_name" \
	    . || exit $$?; \
	done
	@echo
	@echo "✅ All Infinito dev images built."

docker-build-no-cache:
	@echo "============================================================"
	@echo ">>> Building Infinito dev containers (NO CACHE) for: $(DISTROS)"
	@echo "============================================================"
	@for distro in $(DISTROS); do \
	  base_image="$(call _infinito_base_image,$$distro)"; \
	  image_name="infinito-dev-$$distro"; \
	  echo; \
	  echo "------------------------------------------------------------"; \
	  echo ">>> Building $$image_name with NO CACHE (BASE_IMAGE=$$base_image)…"; \
	  echo "------------------------------------------------------------"; \
	  docker build \
	    --no-cache \
	    --build-arg BASE_IMAGE="$$base_image" \
	    -t "$$image_name" \
	    . || exit $$?; \
	done
	@echo
	@echo "✅ All Infinito dev images built (no cache)."
