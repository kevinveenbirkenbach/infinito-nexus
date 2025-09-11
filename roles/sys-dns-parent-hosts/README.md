# sys-dns-parent-hosts

Create Cloudflare DNS A/AAAA records only for **parent hosts** (hosts that have children),
and always include the **apex** (SLD.TLD) as a parent.

Examples:
- c.wiki.example.com  -> parent: wiki.example.com
- a.b.example.com     -> parent: b.example.com
- example.com (apex)  -> always included

## Inputs
- parent_dns_domains (list[str], optional): FQDNs to evaluate. If empty, the role flattens CURRENT_PLAY_DOMAINS.
- PRIMARY_DOMAIN (apex), defaults_networks.internet.ip4, optional defaults_networks.internet.ip6
- Flags:
  - parent_dns_enabled (bool, default: true)
  - parent_dns_ipv6_enabled (bool, default: true)
  - parent_dns_proxied (bool, default: false)

## Usage
- Include the role once after your constructor stage has set CURRENT_PLAY_DOMAINS.

## Tests
Unit tests: tests/unit/roles/sys-dns-parent-hosts/filter_plugins/test_parent_dns.py
Run with: pytest -q
