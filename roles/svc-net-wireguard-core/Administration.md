# Administration

## Client

### Setup wireguard
```bash
  pacman -S wireguard-tools
```

### Create Client Keys
```bash
  wg_private_key="$(wg genkey)"
  wg_public_key="$(echo "$wg_private_key" | wg pubkey)"
  echo "PrivateKey: $wg_private_key"
  echo "PublicKey: $wg_public_key"
  echo "PresharedKey: $(wg genpsk)"
```

### Activate Configuration
```bash
  cp /path/to/wg0.conf /etc/wireguard/wg0.conf
  systemctl enable wg-quick@wg0.service --now
```

### Check status
```bash
  systemctl status wg-quick@wg0.service
```

## Other Resources
- https://golb.hplar.ch/2019/01/expose-srv-vpn.html
- https://wiki.archlinux.org/index.php/WireGuard
- https://wireguard.how/server/raspbian/
- https://www.scaleuptech.com/de/blog/was-ist-und-wie-funktioniert-subnetting/