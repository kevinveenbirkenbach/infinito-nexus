# Docker Compose with Web Proxy

This role combines the standard Docker Compose setup with a reverse-proxy for any application.

## Features

- **Docker Compose**  
  Brings up containers, networks, and volumes via the `docker-compose` role.

- **Reverse Proxy**  
  Uses the `sys-stk-front` role to expose your application under a custom domain and port.
