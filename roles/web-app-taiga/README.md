# Taiga

## Description

[Taiga](https://www.taiga.io/) is a powerful and intuitive open-source project management platform tailored for agile teams. Whether you're practicing Scrum, Kanban, or a custom hybrid workflow, Taiga offers a rich, customizable environment to plan, track, and collaborate on your projects — without the complexity of enterprise tools or the vendor lock-in of SaaS platforms.

This Ansible role deploys Taiga in a Docker-based environment, allowing fast, reproducible, and secure installations. It also optionally integrates [OpenID Connect (OIDC)](https://openid.net/connect/) for single sign-on via providers like Keycloak.

---

## Why Taiga?

Taiga is ideal for developers, designers, and agile teams who want:

- ✅ **Beautiful UI:** Clean, modern, and responsive interface.
- 📌 **Agile Workflows:** Supports Scrum, Kanban, Scrumban, and Epics.
- 🗃️ **Backlog & Sprint Management:** Create user stories, tasks, and sprints with ease.
- 📈 **Burn-down Charts & Metrics:** Monitor velocity and progress.
- 🔄 **Custom Workflows:** Define your own states, priorities, and permissions.
- 📎 **Attachments & Wiki:** Collaborate with file uploads and internal documentation.
- 🔐 **SSO/Authentication Plugins:** OpenID Connect, LDAP, GitHub, GitLab and more.
- 🌍 **Multilingual UI:** Used by teams worldwide.

---

## Purpose

This role automates the deployment and configuration of a complete, production-ready Taiga stack using Docker Compose. It ensures integration with common infrastructure tools such as NGINX, PostgreSQL, and RabbitMQ, while optionally enabling OpenID Connect authentication for enterprise-grade SSO.

By using this role, teams can set up Taiga in minutes on Arch Linux systems — whether in a homelab, dev environment, or production cluster.

---

## Features

- 🐳 **Docker-Based Deployment:** Easy containerized setup of backend, frontend, async workers, and events service.
- 🔐 **OIDC (Single Sign-On):** Supported via:
    - [taiga-contrib-openid-auth (robrotheram)](https://github.com/robrotheram/taiga-contrib-openid-auth)
    - [taiga-contrib-oidc-auth (official)](https://github.com/taigaio/taiga-contrib-oidc-auth)
- 📨 **Email Backend:** Supports SMTP and console backends for development.
- 🔁 **Async & Realtime Events:** Includes RabbitMQ and support for Taiga’s event system.
- 🌐 **Reverse Proxy Ready:** Integrates with NGINX using the `sys-stk-front-proxy` role.
- 🧩 **Composable Design:** Integrates cleanly with other Infinito.Nexus infrastructure roles.

---

## Author

Developed and maintained by **Kevin Veen-Birkenbach**  
Email: [kevin@veen.world](mailto:kevin@veen.world)  
Website: [veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license)