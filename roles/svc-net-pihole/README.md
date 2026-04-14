# svc-net-pihole

Deploys [Pi-hole](https://pi-hole.net/) as a network-wide DNS sinkhole for ad and tracker blocking.

## What is Pi-hole?

Pi-hole acts as a DNS server for your network. When a device requests a domain known to serve ads or trackers, Pi-hole returns a null response — blocking the content before it is downloaded. This protects every device on the network without any client-side configuration.

## Features

- Network-wide DNS-level ad and tracker blocking
- Web dashboard for monitoring and managing DNS queries
- Custom blocklist support via gravity
- Upstream DNS configurable (default: Cloudflare `1.1.1.1`)

## Environment Variables

| Variable           | Description                          | Default          |
|--------------------|--------------------------------------|------------------|
| `PIHOLE_DNS_`      | Upstream DNS servers (semicolon-sep) | `1.1.1.1;1.0.0.1` |
| `WEBPASSWORD`      | Admin dashboard password             | generated        |
| `TZ`               | Timezone                             | `Europe/Berlin`  |
| `WEB_PORT`         | Internal web UI port                 | `8053`           |

## Deployment

```bash
APPS=svc-net-pihole make deploy-fresh-kept-apps
```

## Admin UI

After deployment the dashboard is available at:
http://<host>:8053/admin

## DNS Configuration

Point your router's DHCP DNS setting to the host running Pi-hole so all network devices use it automatically.

## References

- [Pi-hole documentation](https://docs.pi-hole.net/)
- [Pi-hole Docker image](https://github.com/pi-hole/docker-pi-hole)
- [Blocklist collection](https://firebog.net/)
