#!/bin/bash
rm -rv /etc/nginx/
rm -rv /etc/infinito.nexus/ca
rm -rv /etc/infinito.nexus/selfsigned
( cd /opt/compose/openresty/ && docker compose down -v  )
