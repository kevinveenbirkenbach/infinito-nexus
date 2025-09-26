# Front Base (HTTPS + Cloudflare + Handlers) 🚀

## Description
**sys-stk-front-base** bootstraps the front layer that most web-facing apps need:
- Ensures the HTTPS base via `sys-svc-webserver-https`
- (Optional) Cloudflare bootstrap (zone lookup, dev mode, purge)
- Wires OpenResty/Nginx handlers
- Leaves per-domain certificate issuance to consumer roles (or pass-through vars to `sys-util-csp-cert` if needed)

> This role is intentionally small and reusable. It prepares the ground so app roles can just render their vHost.

## Responsibilities
- Include `sys-svc-webserver-https` (once per host)
- Include Cloudflare tasks when `DNS_PROVIDER == "cloudflare"`
- Load handler utilities (e.g., `svc-prx-openresty`)
- Stay domain-agnostic: expect `domain` to be provided by the consumer

## Outputs
- Handler wiring completed
- HTTPS base ready (Nginx, ACME webroot)
- Cloudflare prepared (optional)
