# -*- coding: utf-8 -*-
{
    "name": "OAuth HTTPS Redirect URI Fix",
    "version": "18.0.1.0.0",
    "category": "Authentication",
    "summary": "Force HTTPS redirect URIs for OAuth authentication behind reverse proxy",
    "description": """
OAuth HTTPS Redirect URI Fix
============================

This module fixes OAuth redirect URIs when Odoo runs behind a reverse proxy with TLS termination.

The standard auth_oauth module uses request.httprequest.url_root to build redirect URIs,
which may not correctly respect X-Forwarded-Proto headers in all cases.

This module overrides that behavior to use the web.base.url system parameter instead,
ensuring consistent HTTPS redirect URIs for OAuth authentication flows.

Features:
---------
* Forces OAuth redirect URIs to use web.base.url
* Works correctly behind reverse proxies with TLS termination
* Fixes "redirect_uri mismatch" errors with OIDC providers like Keycloak
    """,
    "author": "Infinito.Nexus",
    "website": "https://infinito.nexus",
    "depends": ["auth_oauth"],
    "data": [],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
}
