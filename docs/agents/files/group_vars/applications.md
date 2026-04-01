# applications.yml

This page is the SPOT for agent handling of `group_vars/all/05_applications.yml`.

## Rules

- `group_vars/all/05_applications.yml` is auto-generated and MUST NOT be modified manually.
- Agents MUST treat the file as generated output from setup, not as a source file.
- When application defaults need to change, agents MUST edit the real sources under `roles/*/config/main.yml`, `roles/*/vars/main.yml`, or other generator inputs instead.
- If the generated file needs to be refreshed after source changes, agents MUST regenerate it through the setup/generator flow instead of patching it by hand.

## Source Of Truth

- Generator: [cli/setup/applications/__main__.py](/home/kevinveenbirkenbach/Repositories/github.com/kevinveenbirkenbach/infinito-nexus/cli/setup/applications/__main__.py)
- Generated output path: [05_applications.yml](/home/kevinveenbirkenbach/Repositories/github.com/kevinveenbirkenbach/infinito-nexus/group_vars/all/05_applications.yml)
- Primary inputs: role-local `vars/main.yml` and `config/main.yml`

## Why

The setup flow rebuilds `defaults_applications` automatically. Manual edits to the generated file are unstable, get overwritten, and hide the real source of configuration changes.
