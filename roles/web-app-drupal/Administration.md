# Administration

## Shell access

```bash
docker-compose exec -it application /bin/bash
```

## Drush (inside the container)

```bash
drush --version
drush cr              # Cache rebuild
drush status          # Site status
drush cim -y          # Config import (if using config sync)
drush updb -y         # Run DB updates
```

## Database access (local DB service)

```bash
docker-compose exec -it database /bin/mysql -u drupal -p
```

## Test Email

```bash
docker-compose exec -it application /bin/bash -lc 'echo "Test Email" | sendmail -v your-email@example.com'
```
