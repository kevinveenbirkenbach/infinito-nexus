# Role: srv-composer

This Ansible role composes and orchestrates all necessary HTTPS-layer tasks and HTML-content injections for your webserver domains. It integrates two key sub-roles into a unified workflow:

1. **`sys-srv-web-inj-compose`**
   Injects global HTML snippets (CSS, Matomo tracking, iFrame notifier, custom JavaScript) into responses using Nginx `sub_filter`.
2. **`sys-svc-certs`**
   Handles issuing, renewing, and managing TLS certificates via ACME/Certbot.

By combining encryption setup with content enhancements, this role streamlines domain provisioning for secure, fully-featured HTTP/HTTPS delivery.

## Features

* **Unified HTTPS Orchestration**
  Seamlessly sets up TLS and performs HTML-level content injections in one role.
* **Content Injection**
  Adds global theming, analytics, and custom scripts before `</head>` and tracking noscript tags before `</body>`.
* **Certificate Management**
  Automates cert issuance and renewal via `sys-svc-certs`.
* **Idempotent Workflow**
  Ensures each component runs only once per domain.
* **Simplified Playbooks**
  Call a single role to handle both security (TLS) and user-experience (injections).
