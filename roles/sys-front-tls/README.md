# sys-front-tls

Generic TLS orchestrator that can be plugged in front of any web app reverse proxy.

## Goal

Provide a unified interface for certificates and protocol selection, so application roles
can switch TLS mode without touching app logic.

Supported modes (resolved outside or passed in):

- letsencrypt  -> use (and if missing: issue) Let's Encrypt certs
- self_signed  -> generate and store a self-signed certificate (SAN aware)
- off          -> no TLS, HTTP only

## Inputs

- tls_mode_effective: "letsencrypt" | "self_signed" | "off"
- tls_domain: primary domain (CN fallback)
- tls_domains_san: SAN domains list (optional)
- tls_app_id: application id (used for self-signed path layout)

Plus provider-specific inputs (see provider roles).

## Outputs (facts)

- TLS_CERT_FILE: path to certificate/fullchain PEM (or empty for off)
- TLS_KEY_FILE: path to private key PEM (or empty for off)
- TLS_CA_FILE: optional CA bundle path (usually empty)
- _tls_san: effective SAN list (internal helper)
