#!/bin/bash
# @param $1 hostname from which backup should be pulled

echo "pulling backups from: $1" &&

# error counter
errors=0 &&

echo "loading meta data..." &&

remote_host="backup@$1" &&
echo "host address:         $remote_host" &&

remote_machine_id="$( (ssh "$remote_host" sha256sum /etc/machine-id) | head -c 64 )" &&
echo "remote machine id:    $remote_machine_id" &&

general_backup_machine_dir="/Backups/$remote_machine_id/" &&
echo "backup dir:           $general_backup_machine_dir" &&

remote_backup_types="$(ssh "$remote_host" "find $general_backup_machine_dir -maxdepth 1 -type d -execdir basename {} ;")" &&
echo "backup types:          $remote_backup_types" || exit 1

for backup_type in $remote_backup_types; do
  if [ "$backup_type" != "$remote_machine_id" ]; then
    echo "backup type:              $backup_type" &&
    
    general_backup_type_dir="$general_backup_machine_dir""$backup_type/" &&
    general_versions_dir="$general_backup_type_dir" &&
    local_previous_version_dir="$(ls -d $general_versions_dir* | tail -1)" &&
    echo "last local backup:      $local_previous_version_dir" &&

    remote_backup_versions="$(ssh "$remote_host" ls -d "$general_backup_type_dir"\*)" &&
    echo "remote backup versions:   $remote_backup_versions" &&


    remote_last_backup_dir=$(echo "$remote_backup_versions" | tail -1) &&
    echo "last remote backup:       $remote_last_backup_dir" &&

    remote_source_path="$remote_host:$remote_last_backup_dir/" &&
    echo "source path:              $remote_source_path" &&

    local_backup_destination_path=$remote_last_backup_dir &&
    echo "backup destination:       $local_backup_destination_path" &&

    echo "creating local backup destination folder..." &&
    mkdir -vp "$local_backup_destination_path" &&

    echo "starting backup..."
    rsync_command='rsync -abP --delete --delete-excluded --rsync-path="sudo rsync" --link-dest="'$local_previous_version_dir'" "'$remote_source_path'" "'$local_backup_destination_path'"'

    echo "executing:                $rsync_command"

    retry_count=0
    max_retries=12
    retry_delay=300  # Retry delay in seconds (5 minutes)
    last_retry_start=0
    max_retry_duration=43200  # Maximum duration for a single retry attempt (12 hours)

    while [[ $retry_count -lt $max_retries ]]; do
      echo "Retry attempt: $((retry_count + 1))"
      if [[ $retry_count -gt 0 ]]; then
        current_time=$(date +%s)
        last_retry_duration=$((current_time - last_retry_start))
        if [[ $last_retry_duration -ge $max_retry_duration ]]; then
          echo "Last retry took more than 12 hours, increasing max retries to 12."
          max_retries=12
        fi
      fi
      last_retry_start=$(date +%s)
      eval "$rsync_command"
      rsync_exit_code=$?
      if [[ $rsync_exit_code -eq 0 ]]; then
        break
      fi
      retry_count=$((retry_count + 1))
      sleep $retry_delay
    done

    if [[ $rsync_exit_code -ne 0 ]]; then
      echo "Error: rsync failed after $max_retries attempts"
      ((errors += 1))
    fi
  fi
done
exit $errors;
