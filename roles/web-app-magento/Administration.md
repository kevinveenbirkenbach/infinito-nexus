# Administration

## 🗑️ Cleanup (Remove Instance & Volumes)
```bash
cd {{ PATH_DOCKER_COMPOSE_INSTANCES }}magento/
docker compose down
docker volume rm magento_data
cd {{ PATH_DOCKER_COMPOSE_INSTANCES }} && rm -vR {{ PATH_DOCKER_COMPOSE_INSTANCES }}magento
```

## 🔍 Access Container Shell
```bash
docker compose exec -it application /bin/bash
```

## 🧰 Common Magento CLI Tasks
```bash
# Reindex
docker compose exec -it application bin/magento indexer:reindex

# Flush caches
docker compose exec -it application bin/magento cache:flush

# Enable maintenance mode
docker compose exec -it application bin/magento maintenance:enable

# Disable maintenance mode
docker compose exec -it application bin/magento maintenance:disable

# Recompile DI (when switching modes)
docker compose exec -it application bin/magento setup:di:compile

# Deploy static content (example for English/German)
docker compose exec -it application bin/magento setup:static-content:deploy en_US de_DE -f
```

## 🚀 Performance
```bash
# Production mode
docker compose exec -it application bin/magento deploy:mode:set production

# Developer mode
docker compose exec -it application bin/magento deploy:mode:set developer
```

## 🔐 Admin User
```bash
# Create another admin (example)
docker compose exec -it application bin/magento admin:user:create \
  --admin-user="admin2" \
  --admin-password="ChangeMe_12345" \
  --admin-email="{{ users.administrator.email }}" \
  --admin-firstname="Admin" \
  --admin-lastname="User"
```
