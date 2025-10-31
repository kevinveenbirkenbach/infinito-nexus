# Drupal

## Description

[Drupal](https://www.drupal.org/) is a powerful open-source CMS for building secure, extensible, and content-rich digital experiences.
This role deploys a containerized **Drupal 10/11** instance optimized for production, including **msmtp** for outbound email, **Drush** for CLI administration, and **OpenID Connect (OIDC)** for SSO (e.g., Keycloak, Auth0, Azure AD).

## Overview

* **Flexible Content Model:** Entities, fields, and views for complex data needs.
* **Security & Roles:** Fine-grained access control and active security team.
* **Robust Ecosystem:** Thousands of modules and themes.
* **CLI Automation:** Drush for installs, updates, and configuration import.
* **OIDC SSO:** First-class login via external Identity Providers.

This automated Docker Compose deployment builds a custom Drupal image with Drush and msmtp, wires database credentials and config overrides via environment, and applies OIDC configuration via Ansible/Drush.

## OIDC

This role enables **OpenID Connect** via the `openid_connect` module and configures a **client entity** (e.g., `keycloak`) including endpoints and scopes. Global OIDC behavior (auto-create, link existing users, privacy) is set via `openid_connect.settings`.

## Further Resources

* [Drupal.org](https://www.drupal.org/)
* [OpenID Connect module](https://www.drupal.org/project/openid_connect)

## Credits

Developed and maintained by **Kevin Veen-Birkenbach**
Learn more at [veen.world](https://veen.world)
Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)
License: [Infinito.Nexus NonCommercial License](https://s.infinito.nexus/license)
