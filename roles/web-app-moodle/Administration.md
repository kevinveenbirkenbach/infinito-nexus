# Administration

## Moodle Docker Directory Path

Moodle lives in: ``cd /opt/compose/moodle``

## Upgrade 

```bash
docker exec --user daemon moodle php /opt/bitnami/moodle/admin/cli/upgrade.php --non-interactive
```

## Delete Cache

To clean the cache execute:

```bash
docker exec --user daemon moodle php /opt/bitnami/moodle/admin/cli/purge_caches.php
docker exec --user root moodle rm -rf \
  /bitnami/moodledata/cache/* \
  /bitnami/moodledata/localcache/* \
  /bitnami/moodledata/temp/* \
  /bitnami/moodledata/sessions/*
docker restart moodle
```

## CLI

A detailled Guid how to use the CLI in moodle you will find [here](https://docs.moodle.org/500/de/Administration_%C3%BCber_Kommandozeile).

## General Administration Tasks

### Radical Erase of Setup
To manually erase the full moodle setup inkluding all data execute:

**CLI:**

```bash 
cd /opt/compose/moodle && \
docker compose down -v || {
  echo "docker compose down failed, cleaning up manually"
  rm -rv /mnt/hdd/data/docker/volumes/moodle_*
  docker compose down -v
} && \
rm -rv /opt/compose/moodle
``` 

Afterwards login to the database and execute

**MariaDB:**
```sql
DROP DATABASE IF EXISTS moodle;
```

to delete all data in the database related to this role. 

### Virgin Setup
After the installation you can rerun this role to create a fresh setup of Moodle. 