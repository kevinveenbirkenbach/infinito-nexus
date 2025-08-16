#!/bin/sh

# Check if the necessary parameters are provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <ssl_cert_folder> <docker_compose_instance_directory>"
    exit 1
fi

# Assign parameters
ssl_cert_folder="$1"
docker_compose_instance_directory="$2"
letsencrypt_live_path="$3"
docker_compose_cert_directory="$docker_compose_instance_directory/volumes/certs"

# Copy certificates
cp -RvL "$letsencrypt_live_path/$ssl_cert_folder/"* "$docker_compose_cert_directory" || exit 1

# This code is optimized for mailu
cp -v "$letsencrypt_live_path/$ssl_cert_folder/privkey.pem" "$docker_compose_cert_directory/key.pem" || exit 1
cp -v "$letsencrypt_live_path/$ssl_cert_folder/fullchain.pem" "$docker_compose_cert_directory/cert.pem" || exit 1

# Set correct reading rights
chmod a+r -v "$docker_compose_cert_directory/"*

# Flag to track if any Nginx reload was successful
nginx_reload_successful=false

# Reload Nginx in all containers within the Docker Compose setup
cd "$docker_compose_instance_directory" || exit 1

# Iterate over all services
for service in $(docker compose ps --services); do
    echo "Checking service: $service"
    # Check if Nginx exists in the container
    if docker compose exec -T "$service" which nginx > /dev/null 2>&1; then
        echo "Reloading Nginx for service: $service"
        if docker compose exec -T "$service" nginx -s reload; then
            nginx_reload_successful=true
            echo "Successfully reloaded Nginx for service: $service"
        else
            echo "Failed to reload Nginx for service: $service" >&2
        fi
    else
        echo "Nginx not found in service: $service, skipping."
    fi
done

# Restart all containers if no Nginx reload was successful
if [ "$nginx_reload_successful" = false ]; then
    echo "No Nginx reload was successful. Restarting all Docker containers."
    docker compose restart || exit 1
else
    echo "At least one Nginx reload was successful. No restart needed."
fi
