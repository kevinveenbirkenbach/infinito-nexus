# sys-front-tls-selfsigned

Self-signed TLS provider for sys-front-tls (SAN aware).

## Inputs

- tls_domain
- tls_domains_san (effective SAN list recommended)
- tls_app_id
- tls_selfsigned_base
- tls_selfsigned_days
- tls_selfsigned_key_bits
- tls_selfsigned_subject (C/O/OU/CN)

## Outputs (facts)

- TLS_CERT_FILE
- TLS_KEY_FILE
- TLS_CA_FILE
