# Webserver

This Ansible role installs and configures **Nginx** as a core HTTP/stream server on Arch Linux systems. It provides:

* **HTTP serving** with MIME types, gzip compression, caching, and custom `nginx.conf` templating.
* **TCP/UDP stream support** via the Nginx Streams module.
* **Directory management** for configuration, `sites-available`/`enabled`, cache, and data.
* **Debugging helpers**: log formats and instructions for general and detailed troubleshooting.

## Features

* **Package installation** of `nginx` and `nginx-mod-stream`.
* **Idempotent setup**: tasks run only once per host.
* **Configurable reset and cleanup** modes to purge and recreate directories.
* **Custom `nginx.conf`** template with sensible defaults for performance and security.
* **Stream proxy support**: includes `stream` block for TCP/UDP proxies.
* **Cache directory management**: cleanup and recreation based on `MODE_CLEANUP`.


## Debugging Tips

* **General logs**: `journalctl -f -u nginx`
* **Filter by host**: `journalctl -u nginx -f | grep "{{ inventory_hostname }}"`
* **Enable detailed format**: set `MODE_DEBUG: true` and reload Nginx.
