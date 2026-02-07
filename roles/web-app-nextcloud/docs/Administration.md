# Administration 

Instructions for manual administrative operations like container login, config file edits, and post-update recovery actions.

## Modify Config 🔧

### Enter the Container
```bash
compose exec -it application /bin/sh
```

### Modify the Configuration
Inside the container, install a text editor and edit the config:
```bash
apk add --no-cache nano && nano config/config.php
```

## Logs

The logs you will find here on the host: **/var/lib/docker/volumes/nextcloud_data/_data/data/nextcloud.log**