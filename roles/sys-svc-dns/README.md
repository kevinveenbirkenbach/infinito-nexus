# sys-svc-dns

Bootstrap and maintain **DNS prerequisites** for your web stack on Cloudflare.

This role validates credentials and (by default) ensures:
- **Parent host A/AAAA records** (incl. the **apex** SLD.TLD) via `sys-dns-parent-hosts`
- *(Optional)* **CAA** records for Let’s Encrypt (kept as a commented block you can re-enable)

Runs **once per play** and is safe to include in stacks that roll out many domains.

---

## What it does

1. **Validate `CLOUDFLARE_API_TOKEN`** is present (early fail if missing).
2. **Ensure parent DNS exists** (apex + “parent” FQDNs derived from children):
   - Delegates to [`sys-dns-parent-hosts`](../sys-dns-parent-hosts/README.md)
   - Creates A (and AAAA if enabled upstream) on the Cloudflare zone, optionally proxied.
3. *(Optional)* **CAA records** for all base SLDs (commented in the tasks; enable if you want CAA managed here).

> Parent hosts example:  
> `c.wiki.example.com` → **parent** `wiki.example.com` (plus `example.com` apex)
