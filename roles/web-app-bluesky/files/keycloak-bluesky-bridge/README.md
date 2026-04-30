# Keycloak ↔ Bluesky PDS bridge SPI

A minimal Keycloak event-listener SPI that auto-provisions a Bluesky
PDS account on `REGISTER` / `LOGIN` events for users in the
configured target group, and stores the synthesised app-password back
on the Keycloak user as a custom attribute (`bluesky_app_password`).

The user pastes that password into the official Bluesky web/app
client to complete the bridge — the PDS uses DID-based auth and does
not accept external IdP tokens directly, so app-passwords are the
required handoff format. Per requirement 013 (`web-app-bluesky`
per-role notes) this is the documented OIDC/LDAP integration path
for Bluesky; the RBAC integration is not feasible because the PDS
has no in-app role concept beyond "account exists / does not exist".

## Build

```sh
mvn -f pom.xml clean package
```

The build produces `target/keycloak-bluesky-bridge-1.0.0.jar`. Drop
the JAR into Keycloak's `/opt/keycloak/providers/` directory and
restart Keycloak so the SPI is registered.

## Configuration

The SPI reads its configuration from environment variables on the
Keycloak container:

| Variable                       | Purpose                                                            | Default                       |
|--------------------------------|--------------------------------------------------------------------|-------------------------------|
| `BLUESKY_PDS_URL`              | Base URL of the PDS, e.g. `https://pds.example`.                   | (empty — listener no-ops)     |
| `BLUESKY_PDS_INVITE_CODE`      | Optional invite code for gated PDS deployments.                    | (empty)                       |
| `BLUESKY_BRIDGE_TARGET_GROUP`  | Keycloak group path that opts a user into the bridge.              | `/roles/web-app-bluesky`      |

## Realm wiring

1. In the realm Events tab, enable `bluesky-bridge` under
   "Event Listeners".
2. Create / verify the `/roles/web-app-bluesky` group exists.
3. Members of that group will trigger PDS provisioning on their
   next login.

## Watch points

* PDS handles MUST be sanitised to `[a-z0-9-]`. The SPI does this
  with a lossy mapping; the sanitised handle is stored back to the
  user attribute so the user sees the actual handle they get.
* Initial provisioning is network-bound on the PLC directory; the
  SPI uses a small retry budget but a network outage on first
  login will require the user to log in again to retry.
* The bridge does NOT delete PDS accounts when the Keycloak user
  is removed — that is a separate cleanup concern out of scope
  for this requirement.
