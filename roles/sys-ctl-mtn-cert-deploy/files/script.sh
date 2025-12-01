#!/bin/sh

# Check if the necessary parameters are provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <ssl_cert_folder> <docker_compose_instance_directory> <letsencrypt_live_path>"
    exit 1
fi

# Assign parameters
ssl_cert_folder="$1"
docker_compose_instance_directory="$2"
letsencrypt_live_path="$3"
docker_compose_cert_directory="${docker_compose_instance_directory}volumes/certs"

# Ensure the target cert directory exists
if [ ! -d "$docker_compose_cert_directory" ]; then
    echo "Creating certs directory: $docker_compose_cert_directory"
    mkdir -p "$docker_compose_cert_directory" || exit 1
fi

# Copy all certificates (generic)
cp -RvL "${letsencrypt_live_path}/${ssl_cert_folder}/"* "$docker_compose_cert_directory" || exit 1

# Mailu optimization: explicit key/cert mapping
cp -v "${letsencrypt_live_path}/${ssl_cert_folder}/privkey.pem"   "${docker_compose_cert_directory}/key.pem"  || exit 1
cp -v "${letsencrypt_live_path}/${ssl_cert_folder}/fullchain.pem" "${docker_compose_cert_directory}/cert.pem" || exit 1

# Set correct reading rights
chmod a+r -v "${docker_compose_cert_directory}/"* || exit 1

# Flags to track Nginx reload status
nginx_reload_successful=false
nginx_reload_failed=false
failed_services=""

# Reload Nginx in all containers within the Docker Compose setup
cd "$docker_compose_instance_directory" || exit 1

echo "Wait for 5 minutes to prevent interuption of setup procedures"
sleep 300

# Iterate over all services
for service in $(docker compose ps --services); do
    echo "Checking service: $service"

    # Check if Nginx exists in the container
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

# Optional auto-healing: restart only the services whose reload failed
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
