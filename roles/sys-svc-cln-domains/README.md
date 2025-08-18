# sys-svc-cln-domains

## Description

This Ansible role removes Nginx configuration files and revokes and deletes Certbot certificates for domains marked as deprecated.

## Overview

Optimized for idempotent cleanup operations, this role:

- Deletes Nginx server configuration files in `/etc/nginx/conf.d/http/servers/` for each domain listed in `deprecated_domains`.
- Revokes and deletes corresponding Certbot certificates.
- Ensures cleanup tasks execute only once per playbook run.
- Notifies Nginx to restart after removing configurations.

## Purpose

Streamline the decommissioning of outdated or deprecated domains by automating the removal of Nginx server blocks and their SSL certificates.

## Features

- **Nginx Cleanup:** Safely removes server configuration files.
- **Certbot Integration:** Revokes and deletes certificates without manual intervention.
- **Idempotent Execution:** Utilizes a `run_once` flag to prevent repeated runs.
- **Service Notification:** Triggers an Nginx restart handler upon cleanup.