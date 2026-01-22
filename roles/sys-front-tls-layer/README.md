# sys-front-tls-layer

Generic TLS layer that can be plugged in front of any web app reverse proxy.

## Goal

Provide a unified interface for certificates and protocol selection, so application roles
can switch the "encryption layer" without touching app logic.

Supported modes:

- letsencrypt  -> use (and if missing: issue) Let's Encrypt certs
- self_signed  -> generate and store a self-signed certificate (SAN aware)
- off          -> no TLS, HTTP only

## Outputs (facts)

- TLS_CERT_FILE: path to certificate/fullchain PEM (or empty for off)
- TLS_KEY_FILE: path to private key PEM (or empty for off)
- TLS_CA_FILE: optional CA bundle path (usually empty)

