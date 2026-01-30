#!/bin/sh
set -eu

# Usage: script.sh <ssl_cert_source_dir> <docker_compose_instance_directory>
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <ssl_cert_source_dir> <docker_compose_instance_directory>" >&2
  exit 1
fi

ssl_cert_source_dir="$1"
docker_compose_instance_directory="$2"

# Keep your existing target layout (minimal change)
docker_compose_cert_directory="${docker_compose_instance_directory}volumes/certs"

if [ ! -d "$ssl_cert_source_dir" ]; then
  echo "ERROR: ssl_cert_source_dir does not exist or is not a directory: $ssl_cert_source_dir" >&2
  exit 1
fi

# Ensure the target cert directory exists
if [ ! -d "$docker_compose_cert_directory" ]; then
  echo "Creating certs directory: $docker_compose_cert_directory"
  mkdir -p "$docker_compose_cert_directory"
fi

echo "Copying certificates from: $ssl_cert_source_dir -> $docker_compose_cert_directory"
cp -RvL "${ssl_cert_source_dir}/"* "$docker_compose_cert_directory"

# Mailu optimization: create key.pem/cert.pem from whatever exists
# Prefer LE naming if present
if [ -f "${ssl_cert_source_dir}/privkey.pem" ] && [ -f "${ssl_cert_source_dir}/fullchain.pem" ]; then
  cp -v "${ssl_cert_source_dir}/privkey.pem"   "${docker_compose_cert_directory}/key.pem"
  cp -v "${ssl_cert_source_dir}/fullchain.pem" "${docker_compose_cert_directory}/cert.pem"
elif [ -f "${ssl_cert_source_dir}/key.pem" ] && [ -f "${ssl_cert_source_dir}/cert.pem" ]; then
  cp -v "${ssl_cert_source_dir}/key.pem"  "${docker_compose_cert_directory}/key.pem"
  cp -v "${ssl_cert_source_dir}/cert.pem" "${docker_compose_cert_directory}/cert.pem"
else
  echo "ERROR: Could not determine key/cert mapping for Mailu." >&2
  echo "Looked for: privkey.pem+fullchain.pem OR key.pem+cert.pem in: $ssl_cert_source_dir" >&2
  exit 1
fi

# Set correct reading rights
chmod a+r -v "${docker_compose_cert_directory}/"* || exit 1

# Flags to track Nginx reload status
nginx_reload_successful=false
nginx_reload_failed=false
failed_services=""

# Reload Nginx in all containers within the Docker Compose setup
cd "$docker_compose_instance_directory" || exit 1

echo "Wait for 5 minutes to prevent interruption of setup procedures"
sleep 300

for service in $(docker compose ps --services); do
  echo "Checking service: $service"

  if docker compose exec -T "$service" which nginx > /dev/null 2>&1; then
    echo "Testing Nginx config for service: $service"
    if ! docker compose exec -T "$service" nginx -t; then
      echo "Nginx config test FAILED for service: $service" >&2
      nginx_reload_failed=true
      failed_services="$failed_services $service"
      continue
    fi

    echo "Reloading Nginx for service: $service"
    if docker compose exec -T "$service" nginx -s reload; then
      nginx_reload_successful=true
      echo "Successfully reloaded Nginx for service: $service"
    else
      echo "Failed to reload Nginx for service: $service" >&2
      nginx_reload_failed=true
      failed_services="$failed_services $service"
    fi
  else
    echo "Nginx not found in service: $service, skipping."
  fi
done

if [ "$nginx_reload_failed" = true ]; then
  echo "At least one Nginx reload failed. Affected services:${failed_services}"
  echo "Restarting affected services to apply the new certificates..."
  # shellcheck disable=SC2086
  (sleep 120 && docker compose restart $failed_services) || (sleep 120 && docker compose restart) || exit 1
elif [ "$nginx_reload_successful" = true ]; then
  echo "At least one Nginx reload was successful. No restart needed."
else
  echo "No Nginx instances found in any service. Nothing to reload."
fi
