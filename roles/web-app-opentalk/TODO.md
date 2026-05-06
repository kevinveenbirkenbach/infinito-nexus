# web-app-opentalk TODO 📝

- [ ] Browser-walk an end-to-end meeting flow: log in via Keycloak, create a meeting, join from a second browser, and verify media flows over the LiveKit relay.
- [ ] Browser-walk an end-to-end recording flow: start a meeting, kick off a recording, and verify the recorder uploads the resulting MP4 to MinIO.
- [ ] Add MinIO bucket policy hardening and a dedicated service account (the controller currently uses MinIO root credentials).
