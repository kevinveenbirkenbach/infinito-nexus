# Jenkins

## Description

[Jenkins](https://www.jenkins.io/) is an open-source automation server that orchestrates the build, test, and deployment of software through pipelines, freestyle jobs, and a large plugin ecosystem.

## Overview

This role deploys Jenkins on Docker Compose. It builds a custom Jenkins image that pre-installs the `oic-auth`, `ldap`, `role-strategy`, and `configuration-as-code` plugins, then mounts a JCasC YAML file that wires the security realm against Keycloak (variant 0, OIDC) or `svc-db-openldap` (variant 1, LDAP). The setup wizard is skipped via `JAVA_OPTS=-Djenkins.install.runSetupWizard=false` so the JCasC config takes over from first boot.

## Features

- **Containerized deployment:** Run Jenkins through Docker Compose with the role-specific custom image.
- **Native OIDC SSO:** Authenticate users against Keycloak via the `oic-auth` plugin, configured by JCasC at boot.
- **LDAP variant:** Switch to Jenkins's core `ldap` plugin via the role's matrix-deploy variant 1 against `svc-db-openldap`.
- **Role-strategy authorisation:** Map Keycloak groups and LDAP groups onto Jenkins authorities through the `role-strategy` plugin.
- **JCasC-managed configuration:** Persist the security realm and authorisation strategy as code via Configuration as Code.
- **Pre-installed plugin set:** Bake build-pipeline, credentials, and SCM plugins into the image so first start-up does not block on plugin downloads.

## Further Resources

- [Jenkins Official Website](https://www.jenkins.io/)
- [Jenkins oic-auth plugin](https://plugins.jenkins.io/oic-auth/)
- [Jenkins Configuration as Code plugin](https://plugins.jenkins.io/configuration-as-code/)

## Credits

Developed and maintained by **Kevin Veen-Birkenbach**.
Learn more at [veen.world](https://www.veen.world).
Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code).
Licensed under the [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license).
