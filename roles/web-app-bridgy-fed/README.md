# Bridgy Fed

## Description
Bridgy Fed bridges ActivityPub (Fediverse), ATProto/Bluesky, and IndieWeb (webmentions/mf2). It mirrors identities and interactions across networks.

## Overview
This role builds and runs Bridgy Fed as a Docker container and (optionally) starts a Datastore-mode Firestore emulator as a sidecar. It exposes HTTP locally for a front proxy.

Upstream docs & dev notes:
- User & developer docs: https://fed.brid.gy and https://bridgy-fed.readthedocs.io/
- Source: https://github.com/snarfed/bridgy-fed
- Local run (reference): `flask run -p 8080` with BRIDGY_APPVIEW_HOST/BRIDGY_PLC_HOST/BRIDGY_BGS_HOST/BRIDGY_PDS_HOST set, and Datastore emulator envs

## Features
- Dockerized Flask app (gunicorn)
- Optional Firestore emulator (Datastore mode) sidecar
- Front proxy integration via `sys-stk-front-proxy`

## Quick start
1) Set domains and ports in inventory.  
2) Enable/disable the emulator in `meta/services.yml`.  
3) Run the role; your front proxy will publish the app.

## Single sign-on

This role does not configure OIDC against `web-app-keycloak`, LDAP
against `svc-db-openldap`, or any role-claim / LDAP-group RBAC
mapping, because Bridgy Fed authenticates users via their fediverse
or atproto credentials at the source platform, not via local
accounts. There is no local user table to bind an external IDP to,
and no in-app authorisation tier to map a Keycloak role or LDAP
group onto. Placing Bridgy Fed behind `web-app-oauth2-proxy` would
break inbound federation traffic and is not supported. This SSO and
RBAC exception is documented per
[lifecycle.md](../../docs/contributing/design/services/lifecycle.md)
and [requirement 013](../../docs/requirements/013-alpha-to-beta-promotion.md).

## Notes
- Emulator is **not** for production; it’s in-memory unless you mount a volume/configure import/export.
