# Todos

## Native Prometheus metrics

`native_metrics.enabled` is set to `false` because the `/metrics` endpoint is compiled out
of `mattermost/mattermost-team-edition` entirely — no env var or config can enable it.

To enable native metrics:
1. Switch to `mattermost/mattermost-enterprise-edition` image in `config/main.yml`
2. Obtain a free Mattermost Starter license (mattermost.com/trial)
3. Add license file handling to the role
4. Set `native_metrics.enabled: true`
