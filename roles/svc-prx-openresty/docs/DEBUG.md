# Debugging OpenResty Configuration

This document provides commands and tips to validate and inspect the OpenResty (Nginx) configuration and the Docker Compose setup.

---

## 1. Validate OpenResty / Nginx Configuration

* **Quick syntax check (quiet):**

  ```bash
  docker exec {{ OPENRESTY_CONTAINER }} openresty -t -q
  ```

  *Returns only errors.*

* **Detailed syntax check (show warnings):**

  ```bash
  docker exec {{ OPENRESTY_CONTAINER }} openresty -t
  ```

  or:

  ```bash
  docker exec {{ OPENRESTY_CONTAINER }} nginx -t
  ```

---

## 2. Dump the Complete Merged Nginx Configuration

To see the full configuration after all `include` directives are processed:

```bash
# Within the running container
docker exec {{ OPENRESTY_CONTAINER }} openresty -T
# or equivalently
docker exec {{ OPENRESTY_CONTAINER }} nginx -T
```

This outputs every directive from `nginx.conf` and all files in `conf.d` in the order Nginx will use them.

---

## 3. Inspect the Docker Compose Configuration

To view the final, merged Docker Compose setup (combining all `docker-compose.yml` files and variable interpolation):

```bash
docker-compose -f docker-compose.yml config
```

If you use a custom project name or multiple override files:

```bash
docker-compose -p <project_name> -f docker-compose.yml -f override.yml config
```

---

### 4. Verifying which domains your TLS certificate covers

To see all hostnames (Subject Alternative Names) included in your certificate, you can inspect the issued `fullchain.pem` file with `openssl`:

```bash
openssl x509 \
  -in /etc/letsencrypt/live/<your-cert-name>/fullchain.pem \
  -noout \
  -text \
| grep -A1 "Subject Alternative Name"
```

This will print something like:

```
            X509v3 Subject Alternative Name:
                DNS:example.com, DNS:www.example.com, DNS:api.example.com
```

Alternatively, you can query the live service directly:

```bash
openssl s_client \
  -connect matrix.cymais.cloud:443 \
  -servername matrix.cymais.cloud \
  </dev/null 2>/dev/null \
| openssl x509 -noout -text \
| grep -A1 "Subject Alternative Name"
```

That way you’ll see exactly which domains your server is serving and which names are valid in the presented certificate.

```
::contentReference[oaicite:0]{index=0}
```

## 5. Common Troubleshooting Tips

* Ensure that all volume mounts and file paths match your host layout.
* Confirm file permissions allow the container to read configuration files.
* Use `-q` for a concise error-only check, omit it to see warnings.
* After fixing issues, reload without downtime:

  ```bash
  docker exec {{ OPENRESTY_CONTAINER }} openresty -s reload
  ```