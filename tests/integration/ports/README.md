# Port Tests 🔌

Integration tests that validate `group_vars/all/09_ports.yml`: every declared port MUST be unique per host/category, and every `ports.<host>.<category>.<service>` reference in the repo MUST resolve to a defined triple.

Tests in this directory MUST only cover port *numbers* and their references. Tests for port-to-application-ID mapping MUST live under `tests/integration/application_id/`, and OAuth2-proxy-specific port rules MUST live under `tests/integration/oauth2_oidc/`.

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../docs/contributing/actions/testing/integration.md).
