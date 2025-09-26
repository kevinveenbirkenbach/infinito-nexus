# Webserver HTTPS Provisioning 🚀

## Description
The **sys-svc-webserver-https** role extends a basic Nginx installation by wiring in everything you need to serve content over HTTPS:

1. Ensures your Nginx server is configured for SSL/TLS.
2. Pulls in Let’s Encrypt ACME challenge handling.
3. Applies global cleanup of unused domain configs.

This role is built on top of your existing `sys-svc-webserver-core` role, and it automates the end-to-end process of turning HTTP sites into secure HTTPS sites.

---

## Overview

When you apply **sys-svc-webserver-https**, it will:

1. **Include** the `sys-svc-webserver-core` role to install and configure Nginx.  
2. **Clean up** any stale vHost files under `sys-svc-cln-domains`.  
3. **Deploy** the Let’s Encrypt challenge-and-redirect snippet from `sys-svc-letsencrypt`.  
4. **Reload** Nginx automatically when any template changes.

All tasks are idempotent—once your certificates are in place and your configuration is set, Ansible will skip unchanged steps on subsequent runs.

---

## Features

- 🔒 **Automatic HTTPS Redirect**  
  Sets up port 80 → 443 redirect and serves `/.well-known/acme-challenge/` for Certbot.

- 🔑 **Let’s Encrypt Integration**  
  Pulls in challenge configuration and CAA-record management for automatic certificate issuance and renewal.

- 🧹 **Domain Cleanup**  
  Removes obsolete or orphaned server blocks before enabling HTTPS.

- 🚦 **Handler-Safe**  
  Triggers an Nginx reload only when necessary, minimizing service interruptions.

---

## License

This role is released under the **Infinito.Nexus NonCommercial License**.
See [https://s.infinito.nexus/license](https://s.infinito.nexus/license) for details.

---

## Author

Developed and maintained by **Kevin Veen-Birkenbach**
Consulting & Coaching Solutions
[https://www.veen.world](https://www.veen.world)
