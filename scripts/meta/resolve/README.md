# Resolve Scripts

This directory contains scripts that resolve metadata and derived values used by the project.

- 🧩 Derive runtime values from repository and workflow context
- 🔍 Resolve identifiers, references, and computed inputs
- 🗂️ Keep lookup and resolution logic grouped in one place

Examples in this folder:
- `repository/name.sh` resolves the concrete repository name once for callers
- `repository/owner.sh` resolves the concrete repository owner once for callers
- `distros.sh` is the SPOT for the canonical distro list used by workflows

The scope of this folder is value resolution.
Build, release, and wait-oriented behavior should stay in their dedicated script directories.
