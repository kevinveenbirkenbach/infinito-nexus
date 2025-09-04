# 🔼 Upgrade

> Always back up the database and the `MAGENTO_VOLUME` volume before upgrades.

1. Update images/versions in the application config (`roles/web-app-magento/config/main.yml` or inventory overrides).
2. Recreate containers:
   ```bash
   cd {{ PATH_DOCKER_COMPOSE_INSTANCES }}magento/
   docker compose pull
   docker compose up -d --remove-orphans
   ```
3. Run upgrade routines:
   ```bash
   docker compose exec -it application bin/magento maintenance:enable
   docker compose exec -it application bin/magento setup:upgrade
   docker compose exec -it application bin/magento setup:di:compile
   docker compose exec -it application bin/magento cache:flush
   docker compose exec -it application bin/magento maintenance:disable
   ```
