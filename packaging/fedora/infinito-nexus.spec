Name:           infinito-nexus
Version:        5.1.0
Release:        1%{?dist}
Summary:        Meta package for Infinito.Nexus host dependencies

License:        LicenseRef-Infinito-Nexus-Community-License
URL:            https://github.com/kevinveenbirkenbach/infinito-nexus
BuildArch:      noarch

Requires:       ansible-core
Requires:       bash
Requires:       ca-certificates
Requires:       curl
Requires:       dbus
Requires:       (docker-ce-cli or docker or moby-engine)
Requires:       docker-compose-plugin
Requires:       gettext
Requires:       git
Requires:       jq
Requires:       make
Requires:       openssh-clients
#
# EL9 AppStream exposes only python3.9 via the generic python3 capability.
# In those environments we still bootstrap Python 3.11+ separately via
# roles/dev-python/files/install.sh, but the RPM metadata must remain
# installable from the stock distro repositories.
%if 0%{?rhel} == 9
Requires:       python3
%else
Requires:       python3 >= 3.11
%endif
Requires:       python3-pip
Requires:       python3-pyyaml
Requires:       rsync
Requires:       sudo
Requires:       systemd
Requires:       tar
Recommends:     bind-utils
Recommends:     shellcheck
Recommends:     shfmt

%description
This package installs the OS-level dependencies required by Infinito.Nexus
development and CI workflows (make, Python, Docker CLI, Ansible controller
tooling, and helper utilities). It intentionally ships no application binaries.

%prep
:

%build
:

%install
install -d %{buildroot}%{_docdir}/%{name}
: > %{buildroot}%{_docdir}/%{name}/DEPENDENCIES

%files
%doc %{_docdir}/%{name}/DEPENDENCIES

%changelog
* Thu Mar 19 2026 Kevin Veen-Birkenbach <kevin@veen.world> - 5.1.0-1
- Add packaging metadata for Debian, Fedora and Arch.
- Centralize OS dependency declarations for Infinito.Nexus host workflows.
