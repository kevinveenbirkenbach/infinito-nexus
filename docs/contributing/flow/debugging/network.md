# Network 🌐

## Docker Pull Errors 🐳

Images cannot be pulled separately, as they run inside a container.

If a `docker pull` or general image pull fails, it may be caused by an MTU, network, or IPv6 issue on the host PC. Check and fix accordingly:

### MTU 📦

Docker defaults to MTU 1500. If the host network uses a smaller MTU (e.g. due to VPN), packets may be dropped or fragmented.

```bash
ip link show docker0
ip link show eth0
```

Fix via `/etc/docker/daemon.json`:

```json
{"mtu": 1450}
```

Then restart Docker:

```bash
sudo systemctl restart docker
```

### IPv6 🔢

If IPv6 is active but misconfigured, Docker may attempt to pull over IPv6 and fail.

```bash
ip -6 addr show
curl -6 https://registry-1.docker.io/v2/
```

The recommended way to disable IPv6 for local development is via Make:

```bash
make disable-ipv6
```

To restore the original IPv6 settings afterwards:

```bash
make restore-ipv6
```

Alternatively, disable IPv6 only in Docker via `/etc/docker/daemon.json`:

```json
{"ipv6": false}
```

### General Connectivity 🔌

```bash
ping -c 3 registry-1.docker.io
curl -v https://registry-1.docker.io/v2/
```

Check firewall rules, proxy settings, and DNS configuration.
