# sys-dns-wildcards

Create Cloudflare DNS **wildcard** A/AAAA records (`*.parent`) only for **parent hosts** (hosts that have children).
The **apex** (SLD.TLD) is considered when computing parents, but **no base host** or `*.apex` record is created by this role.

Examples:
- c.wiki.example.com  -> parent: wiki.example.com -> creates: `*.wiki.example.com`
- a.b.example.com     -> parent: b.example.com    -> creates: `*.b.example.com`
- example.com (apex)  -> used to detect parents, but **no** `example.com` or `*.example.com` record is created

## Inputs
- parent_dns_domains (list[str], optional): FQDNs to evaluate. If empty, the role flattens CURRENT_PLAY_DOMAINS_ALL.
- PRIMARY_DOMAIN (apex), defaults_networks.internet.ip4, optional defaults_networks.internet.ip6
- Flags:
  - parent_dns_enabled (bool, default: true)
  - parent_dns_ipv6_enabled (bool, default: true)
  - parent_dns_proxied (bool, default: false)

## Usage
- Include the role once after your constructor stage has set CURRENT_PLAY_DOMAINS_ALL.
