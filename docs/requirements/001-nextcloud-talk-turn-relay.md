# 001 - Nextcloud Talk TURN relay

## User Story

As an administrator, I want Nextcloud Talk to use a dedicated TURN server so that calls with six or more participants remain stable for clients behind NAT or restrictive firewalls.

## Acceptance Criteria

- [x] A dedicated TURN server is deployed for Nextcloud Talk via `web-svc-coturn` and is reachable externally for STUN/TURN traffic.
- [x] Nextcloud Talk no longer uses the HPB endpoint on port `3480` for STUN/TURN and instead uses the dedicated TURN host, port, and shared secret.
- [x] The required firewall rules are present for the TURN service ports and relay UDP range used by the deployment.
- [x] The Nextcloud Talk administration view shows a valid STUN/TURN configuration without related errors.
- [x] Calls with at least six participants complete reliably without missing video streams, partial connections, or browser-side ICE connection failures caused by missing relay candidates.
- [x] Implementation and validation for `web-app-nextcloud` follow the local iteration loop from [iteration.md](../agents/action/iteration.md), starting with `make deploy-fresh-purged-apps APPS=web-app-nextcloud` for the baseline and continuing with `make deploy-reuse-kept-apps APPS=web-app-nextcloud` for normal follow-up iterations.
- [x] The existing role-local Playwright coverage in [playwright.spec.js](../../roles/web-app-nextcloud/files/playwright.spec.js) and [playwright.env.j2](../../roles/web-app-nextcloud/templates/playwright.env.j2) is extended as far as the local setup allows, and when `compose.services.talk.enabled` is true the Playwright flow verifies in the Nextcloud admin interface that the Talk-related TURN/STUN integration is implemented correctly.
