# Nginx Redirect Role

This Ansible role configures Nginx to perform 301 redirects from one domain to another. It handles SSL certificate retrieval for the source domains and sets up the Nginx configuration to redirect to the specified target domains.

## Role Variables

- `domain_mappings`: A list of objects with `source` and `target` properties specifying the domains to redirect from and to.
- `users.administrator.email`: The email used for SSL certificate registration with Let's Encrypt.

## Dependencies

- `srv-https-stack`: A role for setting up HTTPS for Nginx
- `letsencrypt`: A role for managing SSL certificates with Let's Encrypt

## Author Information
This role was created in 2023 by [Kevin Veen-Birkenbach](https://www.veen.world/).