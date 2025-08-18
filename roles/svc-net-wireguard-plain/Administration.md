# Administration

## Create Client Keys

```bash
  wg_private_key="$(wg genkey)"
  wg_public_key="$(echo "$wg_private_key" | wg pubkey)"
  echo "PrivateKey: $wg_private_key"
  echo "PublicKey: $wg_public_key"
  echo "PresharedKey: $(wg genpsk)"
```
