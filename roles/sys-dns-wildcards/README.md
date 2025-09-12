# sys-dns-wildcards

Create Cloudflare DNS **wildcard** A/AAAA records (`*.parent`) for **parent hosts** (hosts that have children) **and** always for the **apex** (SLD.TLD).

Examples:
- c.wiki.example.com  -> parent: wiki.example.com -> creates: `*.wiki.example.com`
- a.b.example.com     -> parent: b.example.com    -> creates: `*.b.example.com`
- example.com (apex)  -> also creates: `*.example.com`

## Inputs
- parent_dns_domains (list[str], optional): FQDNs to evaluate. If empty, the role flattens CURRENT_PLAY_DOMAINS_ALL.
- PRIMARY_DOMAIN (apex), defaults_networks.internet.ip4, optional defaults_networks.internet.ip6
- Flags:
  - parent_dns_enabled (bool, default: true)
  - parent_dns_proxied (bool, default: false)

## Usage
- Include the role once after your constructor stage has set CURRENT_PLAY_DOMAINS_ALL.
