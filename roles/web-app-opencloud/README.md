# OpenCloud (web-app-opencloud)

Sovereign self-hosted file sync, share, and collaboration platform — Heinlein-Group fork of OpenCloud (`opencloudeu/opencloud`), deployed as a single binary with all microservices except the built-in IDP.

## Highlights

- Single-container OpenCloud single-binary deployment
- External Keycloak as OIDC provider (`PROXY_AUTOPROVISION_ACCOUNTS=true`, role mapping via `groups` claim)
- External OpenLDAP as authoritative user/group directory (`svc-db-openldap`)
- Co-deployable with `web-app-nextcloud` (independent canonical hostnames)
- Cross-integration with `web-app-opentalk` for in-meeting file attachments

## Hostnames

- Canonical: `open.cloud.{{ DOMAIN_PRIMARY }}`
- Coexists with `next.cloud.{{ DOMAIN_PRIMARY }}` (Nextcloud) without conflict.

## Identity & Access

See [docs/IAM.md](docs/IAM.md) and [docs/LDAP.md](docs/LDAP.md).

## Documentation

- Upstream docs: <https://docs.opencloud.eu/>
- Image: <https://hub.docker.com/r/opencloudeu/opencloud>
