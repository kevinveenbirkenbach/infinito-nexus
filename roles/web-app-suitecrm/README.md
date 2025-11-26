# SuiteCRM

## Description

Manage your customer relationships with SuiteCRM, a powerful open-source CRM platform extending SugarCRM with advanced modules, workflows, and integrations. This role integrates SuiteCRM into the Infinito.Nexus ecosystem with centralized database, mail, LDAP and OIDC-ready SSO support. 🚀💼

## Overview

This Ansible role deploys SuiteCRM using Docker and the Infinito.Nexus shared stack. It handles:

- MariaDB database provisioning via the `sys-svc-rdbms` role  
- Nginx domain and reverse-proxy configuration  
- Environment variable management through Jinja2 templates  
- Docker Compose orchestration for the **SuiteCRM** application container  
- Native **LDAP** authentication via Symfony’s LDAP configuration  
- OIDC-ready wiring for integration with Keycloak or other OIDC providers (via reverse proxy or plugin)

With this role, you get a production-ready CRM environment that plugs into your existing IAM stack.

## Features

- **Sales & Service CRM:** Accounts, Contacts, Leads, Opportunities, Cases, Campaigns and more 📊  
- **Workflow Engine:** Automate business processes and notifications 🛠️  
- **LDAP Authentication:** Centralize user authentication against OpenLDAP 🔐  
- **OIDC-Ready SSO:** Preconfigured OIDC environment variables for use with plugins or an OIDC reverse proxy 🌐  
- **Config via Templates:** Fully customizable `.env` and `docker-compose.yml` rendered via Jinja2 ⚙️  
- **Health Checks & Logging:** Integrates with Infinito.Nexus health checking and journald logging 📈  
- **Modular Role Composition:** Uses shared roles for DB, proxy and monitoring to keep your stack consistent 🔄  

## Further Resources

- [SuiteCRM Official Website](https://suitecrm.com/) 🌍  
- [SuiteCRM Documentation](https://docs.suitecrm.com/) 📖  
- [Infinito.Nexus Project Repository](https://s.infinito.nexus/code) 🔗  

## OIDC & LDAP Notes

- **LDAP** is configured using Symfony’s environment variables (`AUTH_TYPE=ldap`, `LDAP_*`) so SuiteCRM 8+ can authenticate directly against your OpenLDAP service.  
- **OIDC** is provided at the platform level (e.g. Keycloak + oauth2-proxy or a SuiteCRM OIDC plugin).  
  This role exposes OIDC client, issuer and endpoint settings as environment variables, so plugins or
  sidecar components can consume them without duplicating configuration.

## Credits

Developed and maintained by **Kevin Veen-Birkenbach**.  
Consulting & Coaching Solutions: [veen.world](https://www.veen.world) 🌟  
Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code) 📂  
License: [Infinito.Nexus NonCommercial License](https://s.infinito.nexus/license) ⚖️  
