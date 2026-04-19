# -*- coding: utf-8 -*-
{
    "name": "OAuth HTTPS & Preferred Username",
    "version": "18.0.1.1.0",
    "category": "Authentication",
    "summary": "Force HTTPS redirect URIs and use preferred_username for OAuth",
    "description": """
OAuth HTTPS & Preferred Username
================================

This module provides two fixes for OAuth authentication with OIDC providers like Keycloak:

1. HTTPS Redirect URIs
----------------------
The standard auth_oauth module uses request.httprequest.url_root to build redirect URIs,
which may not correctly respect X-Forwarded-Proto headers behind a reverse proxy.

This module overrides that behavior to use the web.base.url system parameter instead,
ensuring consistent HTTPS redirect URIs for OAuth authentication flows.

2. Preferred Username Claim
---------------------------
Standard Odoo uses 'user_id' from the OAuth userinfo response to identify users.
This claim is non-standard; Keycloak maps its internal UUID to it by default.

This module changes user identification to use 'preferred_username', which is the
standard OIDC claim for usernames. This aligns Odoo with other applications:
- Mastodon: OIDC_UID_FIELD = preferred_username
- Pixelfed: PF_OIDC_FIELD_ID = preferred_username
- EspoCRM: OIDC_USERNAME_CLAIM = preferred_username
- Taiga: OIDC_USERNAME_CLAIM = preferred_username

Features:
---------
* Forces OAuth redirect URIs to use web.base.url
* Uses preferred_username (not user_id) for user identification
* Works correctly behind reverse proxies with TLS termination
* Consistent with infinito.nexus OIDC identity standards
    """,
    "author": "evangelostsak",
    "website": "https://infinito.nexus",
    "depends": ["auth_oauth"],
    "data": [],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
}
