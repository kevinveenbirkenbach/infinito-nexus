# Administration Notes

## Check configuration

```bash
./launcher enter application
pry(main)> SiteSetting.all.each { |setting| puts "#{setting.name}: #{setting.value}" }
```
---

## Reinitialize Container

To reinitialize the container execute:

```bash
docker network connect discourse_default central-postgres && /opt/docker/discourse/services/repository/launcher rebuild discourse_application
```

### 🔍 Logging with `journalctl`

All build actions triggered by this role are logged to the system journal using `systemd-cat`. Output is simultaneously shown in the terminal and available via `journalctl`.

To view logs for a specific application:

```bash
journalctl -t rebuild-discourse -f
```
