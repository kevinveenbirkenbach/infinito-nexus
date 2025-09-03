# ⚙️ Installation & First Run

## 1) Prepare DNS & Ports
Ensure a canonical domain is mapped (e.g. `shop.{{ PRIMARY_DOMAIN }}`) and a free localhost port in `group_vars/all/10_ports.yml`:
```
web-app-magento: 80xx
```

## 2) Seed Credentials
Provide (at minimum) an admin password in your inventory (vault recommended):
```yaml
applications:
  web-app-magento:
    credentials:
      admin_password: "use-a-strong-secret"
```
The admin username/email are taken from `users.administrator.*`.

## 3) Deploy
Run the Infinito.Nexus playbook for your host(s). The role will:
- Start OpenSearch (single node)
- Start MariaDB (if `central_database` is disabled, the app-local DB is used instead)
- Start Magento application container
- Wire environment via `templates/env.j2`

## 4) Verify
Open your domain (e.g. `https://shop.{{ PRIMARY_DOMAIN }}`) and complete any remaining onboarding steps in the admin panel.

**Admin Panel:** `{{ domains | get_url('web-app-magento', WEB_PROTOCOL) }}/admin`  
(Default path can vary; set a custom `ADMINURI` later via `bin/magento setup:config:set` if desired.)
