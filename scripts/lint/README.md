# Lint Scripts

This directory contains scripts that run repository lint checks.

- 🧹 Execute focused lint checks for workflows, Ansible, Python, and shell scripts
- 🔎 Keep lint entry points small, explicit, and callable from `make`
- ✅ Separate lint execution from tool installation and environment bootstrap

The scope of this folder is lint execution.
Tool installation belongs in `scripts/install`, while build and test workflows should stay in their dedicated script directories.
