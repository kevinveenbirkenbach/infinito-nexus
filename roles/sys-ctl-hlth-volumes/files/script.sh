#!/bin/bash

status=0

# The first argument is a space-separated list of whitelisted volume IDs
whitelist="${1:-}"
whitelisted_volumes=()
if [ -n "$whitelist" ]; then
    # Split on spaces into a bash array (intentional word-splitting here).
    IFS=' ' read -r -a whitelisted_volumes <<< "$whitelist"
fi

anonymous_volumes=$(container volume ls --format "{{.Name}}" | grep -E '^[a-f0-9]{64}$')

if [ -z "$anonymous_volumes" ]; then
    echo "No anonymous volumes found."
    exit
fi

echo "Anonymous volumes found:"

for volume in $anonymous_volumes; do
    # Check if the volume is in the whitelist
    if printf '%s\n' "${whitelisted_volumes[@]}" | grep -q "^$volume$"; then
        echo "Volume $volume is whitelisted and will be skipped."
        continue
    fi

    container_mount_path=$(container ps -q | xargs -I {} container inspect {} --format="{{range .Mounts}}{{if eq .Name \"$volume\"}}{{.Destination}}{{end}}{{end}}" | tr -d '\n' | xargs)
    if [ "$container_mount_path" == "/var/www/bootstrap" ]; then
        echo "Volume $volume is a bootstrap volume and will be skipped."
        continue
    fi

    ((status++))
        
    container_ids=$(container ps -aq --filter volume="$volume")
    if [ -z "$container_ids" ]; then
        echo "Volume $volume is not used by any running containers."
        continue
    fi

    for container_id in $container_ids; do
        container_name=$(container inspect --format '{{ .Name }}' "$container_id" | sed 's#^/##')
        mount_path=$(container inspect --format "{{ range .Mounts }}{{ if eq .Name \"$volume\" }}{{ .Destination }}{{ end }}{{ end }}" "$container_id")
        
        if [ -n "$mount_path" ]; then
            echo "Volume $volume is used by container $container_name at mount path $mount_path"
        else
            echo "Volume $volume is used by container $container_name, but mount path could not be determined."
        fi
    done
done

exit $status
