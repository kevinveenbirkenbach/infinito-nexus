# Todos
- Enable native Prometheus metrics scraping: change `prometheus.yml.j2` target from public domain to internal container port (`:8067` via `MM_METRICSSETTINGS_LISTENADDRESS`) to bypass nginx/OAuth2 proxy
