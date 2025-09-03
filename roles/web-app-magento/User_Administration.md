# 👤 User Administration

- Access the admin panel at:  
  `{{ domains | get_url('web-app-magento', WEB_PROTOCOL) }}/admin`  
  *(or your custom admin path if configured)*

- New admin accounts can be created via the web UI or CLI:
  ```bash
  docker compose exec -it application bin/magento admin:user:create \
    --admin-user="john" \
    --admin-password="SuperSecret_12345" \
    --admin-email="john@example.com" \
    --admin-firstname="John" \
    --admin-lastname="Doe"
  ```
