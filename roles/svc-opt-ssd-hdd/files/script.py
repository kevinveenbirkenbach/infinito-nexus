import subprocess
import os
import time
import sys
import shutil
import argparse


def run_command(command):
    """ Run a shell command and return its output """
    print(command)
    output = subprocess.check_output(command, shell=True).decode('utf-8').strip()
    print(output)
    return output


def stop_containers(containers):
    """Stop a list of containers."""
    container_list = ' '.join(containers)
    print(f"Stopping containers {container_list}...")
    run_command(f"docker stop {container_list}")


def start_containers(containers):
    """Start a list of containers."""
    container_list = ' '.join(containers)
    print(f"Starting containers {container_list}...")
    run_command(f"docker start {container_list}")


def is_database(image):
    databases = {"postgres", "mariadb", "redis", "memcached", "mongo"}
    prefix = image.split(':')[0]
    return prefix in databases


def is_symbolic_link(file_path):
    return os.path.islink(file_path)


def get_volume_path(volume):
    return run_command(f"docker volume inspect --format '{{{{ .Mountpoint }}}}' {volume}")


def get_image(container):
    return run_command(f"docker inspect --format='{{{{.Config.Image}}}}' {container}")


def has_healthcheck(container):
    """Check if a container has a HEALTHCHECK defined."""
    result = run_command(
        f"docker inspect --format='{{{{json .State.Health}}}}' {container}"
    )
    return result not in ("null", "")


def get_health_status(container):
    """Return the health status."""
    status = run_command(
        f"docker inspect --format='{{{{.State.Health.Status}}}}' {container}"
    )
    return status


def run_rsync(src, dest):
    run_command(f"rsync -aP --remove-source-files {src} {dest}")


def delete_directory(path):
    """Deletes a directory and all its contents."""
    try:
        shutil.rmtree(path)
        print(f"Directory {path} was successfully deleted.")
    except OSError as e:
        print(f"Error deleting directory {path}: {e}")


def pause_and_move(storage_path, volume, volume_path, containers):
    stop_containers(containers)
    storage_volume_path = os.path.join(storage_path, 'data', 'docker', 'volumes', volume)
    os.makedirs(storage_volume_path, exist_ok=False)
    run_rsync(f"{volume_path}/", f"{storage_volume_path}/")
    delete_directory(volume_path)
    os.symlink(storage_volume_path, volume_path)
    start_containers(containers)


def has_container_with_database(containers):
    for container in containers:
        image = get_image(container)
        if is_database(image):
            return True
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Migrate Docker volumes to SSD or HDD based on container image.'
    )
    parser.add_argument(
        '--rapid-storage-path', type=str, required=True,
        help='Path to the SSD storage'
    )
    parser.add_argument(
        '--mass-storage-path', type=str, required=True,
        help='Path to the HDD storage'
    )
    args = parser.parse_args()

    rapid_storage_path = args.rapid_storage_path
    mass_storage_path = args.mass_storage_path

    volumes = run_command("docker volume ls -q").splitlines()

    for volume in volumes:
        volume_path = get_volume_path(volume)
        containers = run_command(
            f"docker ps -q --filter volume={volume}"
        ).splitlines()

        if not containers:
            print(f"Skipped Volume {volume}. It does not belong to a running container.")
            continue
        if is_symbolic_link(volume_path):
            print(f"Skipped Volume {volume}. The storage path {volume_path} is a symbolic link.")
            continue

        # Wait until containers with a healthcheck are healthy (not starting or unhealthy)
        for container in containers:
            if has_healthcheck(container):
                status = get_health_status(container)
                while status != 'healthy':
                    print(f"Warte auf Container {container}, Status '{status}'...")
                    time.sleep(1)
                    status = get_health_status(container)

        # Proceed with migration
        if has_container_with_database(containers):
            print(f"Safing volume {volume} on SSD.")
            pause_and_move(rapid_storage_path, volume, volume_path, containers)
        else:
            print(f"Safing volume {volume} on HDD.")
            pause_and_move(mass_storage_path, volume, volume_path, containers)

    print("Operation completed.")
