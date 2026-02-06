#!/bin/sh

docker_ps_grep_unhealthy="$(docker ps --filter health=unhealthy --format '{{.Names}}')"
docker_ps_grep_exited="$(docker ps --filter status=exited --format '{{.ID}}')"

exitcode=0
summary=""

if [ -n "$docker_ps_grep_unhealthy" ]; then
    echo "❌ Some docker containers are unhealthy:"
    echo "$docker_ps_grep_unhealthy"
    echo

    for container_name in $docker_ps_grep_unhealthy
    do
        echo "------------------------------------------------------------"
        echo "🔍 Last 200 log lines for unhealthy container: $container_name"
        echo "------------------------------------------------------------"
        docker logs --tail 200 "$container_name" 2>&1 || echo "⚠️ Failed to fetch logs for $container_name"
        echo

        summary="$summary\n - $container_name (unhealthy)"
    done

    if [ "$exitcode" -lt 1 ]; then
        exitcode=1
    fi
fi

if [ -n "$docker_ps_grep_exited" ]; then
    for container_id in $docker_ps_grep_exited
    do
        container_exit_code="$(docker inspect "$container_id" --format='{{.State.ExitCode}}')"
        container_name="$(docker inspect "$container_id" --format='{{.Name}}')"
        container_name="${container_name#/}"

        if [ "$container_exit_code" -ne "0" ]; then
            echo "❌ Container $container_name exited with code $container_exit_code"
            echo "------------------------------------------------------------"
            echo "🔍 Last 200 log lines for exited container: $container_name"
            echo "------------------------------------------------------------"
            docker logs --tail 200 "$container_name" 2>&1 || echo "⚠️ Failed to fetch logs for $container_name"
            echo

            summary="$summary\n - $container_name (exited: $container_exit_code)"

            if [ "$exitcode" -lt 2 ]; then
                exitcode=2
            fi
        fi
    done
fi

if [ "$exitcode" -ne "0" ]; then
    echo "============================================================"
    echo "🚨 SUMMARY: Unhealthy / Failed Docker Containers"
    echo "============================================================"
    if [ -n "$summary" ]; then
        printf "%b\n" "$summary"
    else
        echo " - (no details collected)"
    fi
    echo "============================================================"
    exit $exitcode
fi

echo "✅ All docker containers are healthy."
exit 0
