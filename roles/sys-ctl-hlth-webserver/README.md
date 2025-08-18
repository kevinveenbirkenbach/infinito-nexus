# sys-ctl-hlth-webserver

## Description
Verifies that each of your Nginx‐served domains returns an expected HTTP status (200, 301, etc.) and alerts on deviations.

## Features
- Scans your `nginx` server block `.conf` files for domains.
- HEAD-requests each domain and compares against per-domain expected codes.
- Reports any mismatches via `sys-ctl-alm-compose`.
- Scheduled via a systemd timer for periodic health sweeps.

## Usage
Include this role, install `python-requests`, and define `on_calendar_health_nginx`.

## Further Resources
- For more details on nginx configurations, visit [nginx documentation](https://nginx.org/en/docs/).
- Learn more about Ansible's `uri_module` [here](https://docs.ansible.com/ansible/latest/modules/uri_module.html).

## Contributions
This role was created with the assistance of ChatGPT. The conversation can be found [here](https://chat.openai.com/share/4033be29-12a6-40a3-bf3c-fc5d57dba8cb) and [here](https://chat.openai.com/share/7f3766d1-9db7-4976-8fe9-68d1142c0a78).