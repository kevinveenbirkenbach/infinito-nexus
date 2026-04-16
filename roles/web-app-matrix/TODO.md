# Todo 
- Enable Whatsapp by default
- Enable Telegram by default
- Enable Slack by default
- Enable ChatGPT by default
- Fix TLS cert to include `matrix.infinito.example` in the SAN list (prerequisite for metrics scraping)
- Enable native Prometheus metrics scraping: change `prometheus.yml.j2` target from public domain to internal Synapse metrics port to bypass nginx/OAuth2 proxy; enable `enable_metrics: true` in homeserver.yaml