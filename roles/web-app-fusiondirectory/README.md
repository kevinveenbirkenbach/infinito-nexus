# FusionDirectory

## Description

This Ansible role deploys and configures [FusionDirectory](https://www.fusiondirectory.org/)—a web-app-based LDAP administration tool—using Docker Compose. It runs a pre-configured FusionDirectory container, connects it to your existing LDAP service, and ensures a consistent, repeatable setup.

## Overview

- Loads and templating of FusionDirectory-specific variables  
- Generates a `.env` file for the container environment  
- Deploys the FusionDirectory container via Docker Compose  
- Configures NGINX (via the `srv-proxy-6-6-domain` role) to expose the service  
- Integrates with your central LDAP server for authentication  

## Features

- **Easy Deployment:** Runs FusionDirectory in Docker Compose with minimal manual steps  
- **LDAP Integration:** Connects to your existing LDAP backend for user management  
- **Environment Management:** Builds an environment file from role variables and templates  
- **NGINX Setup:** Automatically configures a virtual host for FusionDirectory  
- **Docker-Native:** Leverages the `docker-compose` role for container orchestration  
- **Idempotent:** Safe to run multiple times without side effects  

## Further Resources

- [FusionDirectory Official Website](https://www.fusiondirectory.org/)  
- [FusionDirectory Docker Image (tiredofit/fusiondirectory)](https://hub.docker.com/r/tiredofit/fusiondirectory)  
- [Role Source & Documentation (Infinito.Nexus)](https://s.infinito.nexus/code/tree/main/roles/web-app-fusiondirectory)  
- [Infinito.Nexus NonCommercial License (CNCL)](https://s.infinito.nexus/license)  
