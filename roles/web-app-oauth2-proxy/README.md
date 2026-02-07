# OAuth2 Proxy

Welcome to the **OAuth2 Proxy Role**! 🌟 This role contains helper functions to set up an OAuth2 proxy using [OAuth2 Proxy](https://github.com/oauth2-proxy/oauth2-proxy), a tool designed to secure applications by protecting them with OAuth2 authentication. 💡

## Overview

The OAuth2 Proxy is used to shield specific web applications from unauthorized access by requiring users to authenticate via an external identity provider, such as Keycloak. This role simplifies the setup process by providing templated configurations and tasks to integrate the OAuth2 Proxy with Docker Compose and Keycloak.

## Features

- 🚀 Automated configuration transfer to your Docker Compose instance.
- 🔧 Template files for a fully customizable proxy setup.
- 🔐 Integration with Keycloak as an OpenID Connect (OIDC) provider.
- 🛡️ Configurations to secure applications and allow cookie-based authentication across subdomains.

## How It Works

The role includes the following key components:

1. **Templates**:
    - `oauth2-proxy-keycloak.cfg.j2`: A configuration file for the OAuth2 Proxy, pre-integrated with Keycloak as an identity provider.
    - `container.yml.j2`: A container definition for the OAuth2 Proxy, specifying the image, ports, volumes, and restart policies.

2. **Tasks**:
    - A task to transfer the templated configuration to the Docker Compose instance directory.
    - A notifier to trigger the setup of the Docker Compose project after transferring the configuration.

3. **Integration**:
    - Keycloak is configured as the OIDC provider, enabling seamless authentication and authorization.
    - Upstream application support ensures traffic is securely proxied to the correct destination.

## Why Use This Proxy?

Using this proxy ensures that only authenticated users can access your protected applications. By leveraging OAuth2, you can:

- ✅ Secure applications with minimal configuration.
- ✅ Enable single sign-on (SSO) and centralized user management.
- ✅ Restrict access to specific domains and subdomains.

## Dependencies

Before using this role, ensure you have the following:

- Docker and Docker Compose installed on your system.
- A running Keycloak instance configured with the appropriate realm and clients.

## Learn More

To learn more about OAuth2 Proxy, check out the [official documentation](https://oauth2-proxy.github.io/oauth2-proxy/).

## Author

This role was created and maintained by **Kevin Veen-Birkenbach**. 🌍 You can learn more about Kevin and his projects at [veen.world](https://www.veen.world).

---

Protect your web applications with ease and confidence! ✨

