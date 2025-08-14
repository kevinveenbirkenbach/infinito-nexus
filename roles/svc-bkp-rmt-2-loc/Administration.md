# Administration Tasks

## Debug Instructions

### Live Monitoring

To track what the service is doing, execute one of the following commands:

#### Using systemctl

```bash
watch -n2 "systemctl status sys-bkp-rmt-2-loc{{ SYS_SERVICE_SUFFIX }}"
```

#### Using journalctl

```bash
journalctl -fu sys-bkp-rmt-2-loc{{ SYS_SERVICE_SUFFIX }}
```

### Viewing History

```bash
sudo journalctl -u sys-bkp-rmt-2-loc{{ SYS_SERVICE_SUFFIX }}
```