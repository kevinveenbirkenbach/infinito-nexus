# TODO — web-app-opentalk

- [ ] Browser-walk an end-to-end meeting flow: log in via Keycloak, create a meeting, join from a second browser, and verify media via LiveKit relay.
- [ ] Add an nginx/openresty location for `/livekit` on `talk.{{ DOMAIN_PRIMARY }}` that upgrades to `wss://` and forwards to the LiveKit container's host port 7880 (currently the controller toml references `wss://talk.<DOMAIN>/livekit` but the front proxy does not route that path yet).
- [ ] Add MinIO bucket policy hardening + dedicated service account (currently the controller uses MinIO root creds).
- [ ] Optional: add the OpenTalk recorder (`registry.opencode.de/opentalk/recorder`) and RabbitMQ if room recordings are wanted.
