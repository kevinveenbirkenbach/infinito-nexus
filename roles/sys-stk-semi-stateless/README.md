# Semi-Stateless Stack (Front + Back) ⚡

## Description
**sys-stk-semi-stateless** combines the front and back layer into a lightweight, mostly stateless web service stack:
- Front bootstrap via `sys-stk-front-base` (HTTPS base, optional Cloudflare, handlers)
- Backend via `sys-stk-back-stateless` (no persistent volumes/DB)

Ideal for services that need TLS/front glue but no database (e.g., TURN/STUN, gateways, simple APIs).

## Responsibilities
- Prepare the front layer (HTTPS / handlers / optional Cloudflare)
- Deploy the stateless backend (typically via Docker Compose)
- Keep domain variables (`domain`) and app-scoped variables (`application_id`) clearly separated
