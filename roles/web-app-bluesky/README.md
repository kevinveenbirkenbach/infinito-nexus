# Bluesky
## Description
Soar to new digital heights with Bluesky, an innovative platform that reimagines social networking with its forward-thinking, community-driven approach. Experience a burst of energy, creativity, and the freedom to connect in a truly inspiring way.
## Overview
This role deploys Bluesky using Docker Compose. It sets up the personal data server (PDS) and the social web service, configures multiple domains via NGINX, downloads and extracts the pdsadmin tool for administration, and clones the social app repository to build a fully orchestrated container environment for Bluesky.
## Developer Notes

For DNS configuration and other setup details, see [Installation.md](./Installation.md).
## Features
- **Decentralized Social Networking:** Engage in a community-driven social platform that prioritizes data ownership and privacy.
- **Innovative Community Moderation:** Utilize advanced tools for managing content and maintaining healthy discussions.
- **Scalable Infrastructure:** Leverage a Dockerized deployment that adapts to growing workloads efficiently.
- **Real-Time Content Delivery:** Enjoy dynamic and instantaneous updates for a modern social experience.
- **Developer-Friendly API:** Integrate with external systems and extend functionalities through a robust set of APIs.

## Single sign-on

OIDC is wired in via a Keycloak event-listener bridge to the PDS
`com.atproto.server.createAccount` endpoint. The bridge stores the
synthesised app-password as a Keycloak user attribute, and the
user's self-service portal surfaces that password so it can be
pasted into the official Bluesky web/app client. LDAP feeds the
same bridge via Keycloak's LDAP federation against
`svc-db-openldap`; direct LDAP-to-PDS sync is not supported, the
Keycloak federation layer is the single source of truth.

RBAC is not feasible: the PDS has no in-app role concept beyond
"account exists / does not exist". This RBAC exception is
documented per
[lifecycle.md](../../docs/contributing/design/services/lifecycle.md)
and [requirement 013](../../docs/requirements/013-alpha-to-beta-promotion.md).

## Further Resources
- [Self-hosting Bluesky with Docker and SWAG](https://therobbiedavis.com/selfhosting-bluesky-with-web-app-and-swag/)
- [Notes on Self-hosting Bluesky PDS with Other Services](https://cprimozic.net/notes/posts/notes-on-self-hosting-bluesky-pds-alongside-other-services/)
- [Bluesky PDS GitHub Repository](https://github.com/bluesky-social/pds)
- [Bluesky Social YouTube Overview](https://www.youtube.com/watch?v=7_AG50u7D6c)
- [Bluesky PDS Issue #52](https://github.com/bluesky-social/pds/issues/52)
- [pdsadmin GitHub Repository](https://github.com/lhaig/pdsadmin)
- [Bluesky PDS Issue #147](https://github.com/bluesky-social/pds/issues/147)
- [OAuth Client Documentation](https://docs.bsky.app/docs/advanced-guides/oauth-client)
## Credits
Developed and maintained by **Kevin Veen-Birkenbach**.
Learn more at [veen.world](https://www.veen.world).
Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code).
Licensed under the [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license).
