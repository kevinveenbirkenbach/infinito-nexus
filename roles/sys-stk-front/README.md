# Nginx Domain Setup 🚀

## Description

This role bootstraps **per-domain Nginx configuration**: it requests TLS certificates, applies global modifiers, deploys a ready-made vHost file, and can optionally lock down access via OAuth2.

## Overview

A higher-level orchestration wrapper, *sys-stk-front* ties together several lower-level roles:

1. **`sys-srv-web-inj-compose`** – applies global tweaks and includes.  
2. **`srv-tls-core`** – obtains Let’s Encrypt certificates.  
3. **Domain template deployment** – copies a Jinja2 vHost from *srv-proxy-core*.  
4. **`web-app-oauth2-proxy`** *(optional)* – protects the site with OAuth2.

The result is a complete, reproducible domain rollout in a single playbook task.

## Purpose

Provide **one-stop, idempotent domain provisioning** for Nginx-based homelabs or small production environments.

## Features

- **End-to-end TLS** — certificate retrieval and secure headers included.  
- **Template-driven vHosts** — choose *basic* or *ws_generic* flavours (or your own).  
- **Conditional OAuth2** — easily toggle authentication per application.  
- **Handler-safe** — automatically triggers an Nginx reload when templates change.  
- **Composable** — designed to be called repeatedly for many domains.

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at <https://www.veen.world>

Part of the **Infinito.Nexus Project** — licensed under the [Infinito.Nexus NonCommercial License](https://s.infinito.nexus/license)