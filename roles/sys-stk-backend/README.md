# Database Docker Composition

This role combines the central RDBMS role (`sys-svc-rdbms`) with Docker Compose to deliver a ready-to-use containerized database environment.

## Features

- **Central RDBMS Integration**  
  Includes the `sys-svc-rdbms` role, which handles backups, restores, user and permission management for your relational database system (PostgreSQL, MariaDB, etc.).

- **Docker Compose**  
  Utilizes the standalone `compose` role to define and bring up containers, networks, and volumes automatically.

The role will load both sub-roles and satisfy all dependencies transparently.

## Task Breakdown

1. **Set Fact** `database_application_id` to work around lazy‐loading ordering.
2. **Include Vars** in the specified order.
3. **Invoke** `compose` role to create containers, networks, and volumes.
4. **Invoke** `sys-svc-rdbms` role to provision the database, backups, and users.