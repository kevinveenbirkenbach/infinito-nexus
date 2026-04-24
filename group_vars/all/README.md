# group_vars/all 📦

This directory contains the [Ansible](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_variables.html) `group_vars` applied to every host in the inventory. It holds the shared baseline that every role and every host-specific var can build on top of.

## Scope 🎯

Variables in this directory MUST apply across all hosts and all roles. Typical examples are the software identity, deployment toggles, domain defaults, the central network and port registries, OIDC and LDAP endpoints, design tokens, and resource defaults.

Role-specific configuration MUST NOT live here. Such values belong in the corresponding role under `roles/<role>/config/main.yml` or `roles/<role>/vars/main.yml`.

## File naming and load order 🔢

Files MUST use the pattern `NN_<topic>.yml`, where `NN` is a zero-padded two-digit numeric prefix. Ansible loads files in lexicographic order, so the prefix determines the load order and lets later files reference values defined earlier.

Prefixes MUST be unique and sequential without gaps. When you add, remove, or reorder a file, you MUST update every hard-coded reference in code, tests, and documentation to keep the sequence consistent. You SHOULD grep for `group_vars/all/<old-name>.yml` before renaming.
