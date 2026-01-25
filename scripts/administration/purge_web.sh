#!/bin/bash
rm -rv /etc/nginx/
( cd /opt/docker/openresty/ && docker compose down -v  )
