# Database Docker with Web Proxy

This role builds on `cmp-db-docker` by adding a reverse-proxy frontend for HTTP access to your database service.

## Features

- **Database Composition**  
  Leverages the `cmp-db-docker` role to stand up your containerized database (PostgreSQL, MariaDB, etc.) with backups and user management.

- **Reverse Proxy**  
  Includes the `srv-domain-provision` role to configure a proxy (e.g. nginx) for routing HTTP(S) traffic to your database UI or management endpoint.