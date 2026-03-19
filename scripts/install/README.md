# Install Scripts

This directory contains scripts that install and bootstrap host-side tooling used by the project.

- 📦 Install Python, Ansible, and lint dependencies for supported environments
- 📦 Build and install distro package metadata via `package.sh` (Arch/Debian/Ubuntu/Fedora)
- 🐍 Bootstrap virtual environments and editable project dependencies
- 🛠️ Keep host preparation separate from lint, build, and test execution

The scope of this folder is installation and bootstrap.
Lint execution, build workflows, and test orchestration should stay in their dedicated script directories.
