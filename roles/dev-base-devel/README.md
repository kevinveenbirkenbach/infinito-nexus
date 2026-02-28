# dev-base-devel Role

This Ansible role installs a base development toolchain across the default Infinito distros.

## Description

The role installs distro-specific equivalents of core build tooling so systems are ready for compiling software from source.

## Usage

After deploying this role, all common build dependencies will be available on the system, allowing you to compile and install software packages that require development tools.

## Features

- Installs distro-specific base development packages:
  - Archlinux: `base-devel`
  - Debian/Ubuntu: `build-essential`
  - Fedora/CentOS: `@development-tools`
- Ensures your system is ready for software compilation and development

## Further Resources

- [Arch Wiki: base-devel](https://wiki.archlinux.org/title/Development_packages)
- [Debian package: build-essential](https://packages.debian.org/stable/build-essential)
- [DNF groups: development-tools](https://dnf.readthedocs.io/en/latest/command_ref.html#group-command)
