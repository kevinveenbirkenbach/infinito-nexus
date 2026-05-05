# TODO — web-app-opencloud

- [ ] Browser-walk an end-to-end OIDC login (Keycloak → OpenCloud → autoprovisioned LDAP user lands on Files view).
- [ ] Confirm `application_administrators` LDAP-group members get the OpenCloud admin role at runtime.
- [ ] Surface OpenTalk in the OpenCloud sidebar (currently only `WEB_OPTION_OPENTALK_URL` is set; an upstream app/extension is required for a clickable launcher).
- [ ] Verify back-channel logout from Keycloak terminates the OpenCloud session in a real browser.
