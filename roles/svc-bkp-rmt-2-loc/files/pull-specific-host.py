#!/usr/bin/env python3
import argparse
import os
import subprocess
import time
import sys


def run_command(command, capture_output=True, check=False, shell=True):
    """Run a shell command and return its output as string."""
    try:
        result = subprocess.run(
            command, capture_output=capture_output, shell=shell, text=True, check=check
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if capture_output:
            print(e.stdout)
            print(e.stderr)
        raise


def pull_backups(hostname: str):
    print(f"pulling backups from: {hostname}")
    errors = 0

    print("loading meta data...")
    remote_host = f"backup@{hostname}"
    print(f"host address:         {remote_host}")

    remote_machine_id = run_command(f'ssh "{remote_host}" sha256sum /etc/machine-id')[
        :64
    ]
    print(f"remote machine id:    {remote_machine_id}")

    general_backup_machine_dir = f"/Backups/{remote_machine_id}/"
    print(f"backup dir:           {general_backup_machine_dir}")

    try:
        remote_backup_types = run_command(
            f'ssh "{remote_host}" "find {general_backup_machine_dir} -maxdepth 1 -type d -execdir basename {{}} ;"'
        ).splitlines()
        print(f"backup types:          {' '.join(remote_backup_types)}")
    except subprocess.CalledProcessError:
        sys.exit(1)

    for backup_type in remote_backup_types:
        if backup_type == remote_machine_id:
            continue

        print(f"backup type:              {backup_type}")

        general_backup_type_dir = f"{general_backup_machine_dir}{backup_type}/"
        general_versions_dir = general_backup_type_dir

        # local previous version
        try:
            local_previous_version_dir = run_command(
                f"ls -d {general_versions_dir}* | tail -1"
            )
        except subprocess.CalledProcessError:
            local_previous_version_dir = ""
        print(f"last local backup:      {local_previous_version_dir}")

        # remote versions
        remote_backup_versions = run_command(
            f'ssh "{remote_host}" "ls -d /Backups/{remote_machine_id}/backup-docker-to-local/*"'
        ).splitlines()
        print(f"remote backup versions:   {' '.join(remote_backup_versions)}")

        remote_last_backup_dir = (
            remote_backup_versions[-1] if remote_backup_versions else ""
        )
        print(f"last remote backup:       {remote_last_backup_dir}")

        remote_source_path = f"{remote_host}:{remote_last_backup_dir}/"
        print(f"source path:              {remote_source_path}")

        local_backup_destination_path = remote_last_backup_dir
        print(f"backup destination:       {local_backup_destination_path}")

        print("creating local backup destination folder...")
        os.makedirs(local_backup_destination_path, exist_ok=True)

        rsync_command = (
            f'rsync -abP --delete --delete-excluded --rsync-path="sudo rsync" '
            f'--link-dest="{local_previous_version_dir}" "{remote_source_path}" "{local_backup_destination_path}"'
        )
        print("starting backup...")
        print(f"executing:                {rsync_command}")

        retry_count = 0
        max_retries = 12
        retry_delay = 300  # 5 minutes
        last_retry_start = 0
        max_retry_duration = 43200  # 12 hours

        rsync_exit_code = 1
        while retry_count < max_retries:
            print(f"Retry attempt: {retry_count + 1}")
            if retry_count > 0:
                current_time = int(time.time())
                last_retry_duration = current_time - last_retry_start
                if last_retry_duration >= max_retry_duration:
                    print(
                        "Last retry took more than 12 hours, increasing max retries to 12."
                    )
                    max_retries = 12
            last_retry_start = int(time.time())
            rsync_exit_code = os.system(rsync_command)
            if rsync_exit_code == 0:
                break
            retry_count += 1
            time.sleep(retry_delay)

        if rsync_exit_code != 0:
            print(f"Error: rsync failed after {max_retries} attempts")
            errors += 1

    sys.exit(errors)


def main():
    parser = argparse.ArgumentParser(
        description="Pull backups from a remote backup host via rsync."
    )
    parser.add_argument("hostname", help="Hostname from which backup should be pulled")
    args = parser.parse_args()
    pull_backups(args.hostname)


if __name__ == "__main__":
    main()
