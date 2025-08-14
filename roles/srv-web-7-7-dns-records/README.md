# Cloudflare DNS Records

## Description

This Ansible role automates the management of DNS A-records in Cloudflare zones. It uses the [community.general.cloudflare_dns](https://docs.ansible.com/ansible/latest/collections/community/general/cloudflare_dns_module.html) module to create or update A-records for a list of domains, automatically detects the correct zone for each record, and supports configurable proxy settings.

## Overview

Looping over a provided list of domains (`cloudflare_domains`), this role:
- Determines the zone name by extracting the last two labels of each domain.
- Ensures an A-record for each domain points to the specified IP (`cloudflare_target_ip`).
- Honors the `proxied` flag to switch between DNS-only and Cloudflare-proxied modes.
- Provides an optional debug task (`MODE_DEBUG`) to output the domain list before changes.

Ideal for environments where bulk or dynamic DNS updates are needed, this role abstracts away the complexity of Cloudflare’s zone and record API.

## Purpose

Cloudflare DNS Records delivers an idempotent, scalable solution for managing A-records across multiple Cloudflare zones. Whether you need to onboard hundreds of domains or toggle proxy settings in CI/CD pipelines, this role handles the orchestration and ensures consistency.

## Features

- **Automatic Zone Detection:** Parses each domain to derive its zone (`example.com`) without manual intervention.  
- **Bulk Record Management:** Creates or updates A-records for all entries in `cloudflare_domains`.  
- **Proxy Toggle:** Configure `proxied: true` or `false` per record to switch between DNS-only and proxied modes.  
- **Debug Support:** Enable `MODE_DEBUG` to print the domain list for validation before execution.  
- **Flexible Authentication:** Supports both API token (`api_token`) and Global API key + email.  
- **Low-TTL Option:** Use `ttl: 1` for rapid DNS propagation during dynamic updates.

## Author

Kevin Veen-Birkenbach

## License

Infinito.Nexus NonCommercial License  
<https://s.infinito.nexus/license>