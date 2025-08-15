# Administration 🛠️

## List Unused Volumes
```bash
docker volume ls -q -f "dangling=true"
```

## Remove All Unused Volumes
```bash
docker volume rm $(docker volume ls -q -f "dangling=true")
```

## Network Issues Fixes
```bash
docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)
docker network prune -f
systemctl stop docker
rm -fv /var/lib/docker/network/files/local-kv.db
systemctl start docker
```

---

# Warning ⚠️

**Caution:** The following instructions will delete **all Docker containers and volumes** on your server.  
Make sure you have backups or that you're certain you want to clean your Docker environment completely.

---

## Cleaning Up Docker Containers and Volumes 🧹

### Delete All Docker Containers
```bash
docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)
```

### Delete All Docker Volumes
```bash
docker volume rm $(docker volume ls -q)
```
