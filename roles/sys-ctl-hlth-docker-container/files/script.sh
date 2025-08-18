#!/bin/sh
docker_ps_grep_unhealthy="$(docker ps --filter health=unhealthy --format '{{.Names}}')"
docker_ps_grep_exited="$(docker ps --filter status=exited --format '{{.ID}}')"

exitcode=0

if [ -n "$docker_ps_grep_unhealthy" ]; then 
   echo "Some docker containers are unhealthy: $docker_ps_grep_unhealthy"
   exitcode=1
fi

if [ -n "$docker_ps_grep_exited" ]; then 
   for container_id in $docker_ps_grep_exited
   do
       container_exit_code="$(docker inspect "$container_id" --format='{{.State.ExitCode}}')"
       container_name="$(docker inspect "$container_id" --format='{{.Name}}')"
       container_name="${container_name#/}" # Entfernt das führende '/'
       if [ "$container_exit_code" -ne "0" ]; then
           echo "Container $container_name exited with code $container_exit_code"
           exitcode=2
       fi
   done
fi

if [ "$exitcode" -ne "0" ]; then 
   exit $exitcode
fi

echo "All docker containers are healthy."
exit
