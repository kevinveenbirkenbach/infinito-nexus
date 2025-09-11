# sys-svc-dns

Bootstrap and maintain **DNS prerequisites** for your web stack on Cloudflare.

This role validates credentials and (by default) ensures:
- **Wildcard A/AAAA records** (`*.parent`) for parent hosts via `sys-dns-wildcards` (no base/apex records)
- *(Optional)* **CAA** records for Let’s Encrypt (kept as a commented block you can re-enable)

Runs **once per play** and is safe to include in stacks that roll out many domains.

---

## What it does

1. **Validate `CLOUDFLARE_API_TOKEN`** is present (early fail if missing).
2. **Ensure wildcard parent DNS exists** (`*.parent` derived from children):
   - Delegates to [`sys-dns-wildcards`](../sys-dns-wildcards/README.md)
   - Creates `A` (and `AAAA` if enabled) wildcard records on the Cloudflare zone, optionally proxied. 
3. *(Optional)* **CAA records** for all base SLDs (commented in the tasks; enable if you want CAA managed here).

> Parent hosts example:  
> `c.wiki.example.com` → **parent** `wiki.example.com` (plus `example.com` apex)
