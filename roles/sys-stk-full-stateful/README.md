# Database Docker with Web Proxy

This role builds on `sys-stk-back-stateful` by adding a reverse-proxy frontend for HTTP access to your database service.

## Features

- **Database Composition**  
  Leverages the `sys-stk-back-stateful` role to stand up your containerized database (PostgreSQL, MariaDB, etc.) with backups and user management.

- **Reverse Proxy**  
  Includes the `sys-stk-front-proxy` role to configure a proxy (e.g. nginx) for routing HTTP(S) traffic to your database UI or management endpoint.