# sys-ctl-hlth-webserver
## Description
Verifies that each of your NGINX‐served domains returns an expected HTTP status (200, 301, etc.) and alerts on deviations.
## Features
- Scans your `NGINX` server block `.conf` files for domains.
- HEAD-requests each domain and compares against per-domain expected codes.
- Reports any mismatches via `sys-ctl-alm-compose`.
- Scheduled via a systemd timer for periodic health sweeps.
## Usage
Include this role and define `on_calendar_health_NGINX`.
The role installs `requests` via `pip` automatically.
## Further Resources
- For more details on NGINX configurations, visit [NGINX documentation](https://NGINX.org/en/docs/).
- Learn more about Ansible's `uri_module` [here](https://docs.ansible.com/ansible/latest/modules/uri_module.html).
## Contributions
This role was created with the assistance of ChatGPT.
