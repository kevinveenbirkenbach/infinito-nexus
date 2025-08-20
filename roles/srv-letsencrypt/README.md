# Let’s Encrypt SSL for Nginx 🔐

## Description
Automates obtaining, configuring, and renewing Let’s Encrypt SSL certificates for Nginx with Certbot. Keeps your sites secure with minimal fuss! 🌐

## Overview
This Ansible role sets up the necessary Nginx configuration and Certbot integration to:
- Redirect HTTP traffic to HTTPS  
- Serve the ACME challenge for certificate issuance  
- Apply strong SSL/TLS defaults  
- Schedule automatic renewals  

It’s idempotent: configuration and certificate tasks only run when needed. ✅

## Purpose
Ensure all your Nginx-hosted sites use free, trusted SSL certificates from Let’s Encrypt—all managed automatically via Ansible. 🎯

## Features
- **Automatic Certificate Issuance**: Uses Certbot’s webroot plugin to request and install certificates. 📜  
- **Nginx Redirect**: Creates a temporary HTTP → HTTPS redirect block. ↪️  
- **ACME‐Challenge Handling**: Configures `/.well-known/acme-challenge/` for Certbot validation. 🔍  
- **Secure SSL Defaults**: Includes modern cipher suites, HSTS, OCSP stapling, and session settings. 🔒  
- **Auto‐Renewal**: Leverages system scheduling (cron or systemd timer) to renew certs before expiration. 🔄  
- **One‐Time Setup**: Tasks guarded by a “run once” fact to avoid re-applying unchanged templates. 🏃‍♂️  