import os
import sys
import subprocess
import argparse

def hard_restart_docker_services(dir_path):
    """
    Perform a hard restart of docker-compose services in the given directory
    using docker-compose down and docker-compose up -d.
    """
    try:
        print(f"Performing hard restart for docker-compose services in: {dir_path}")
        subprocess.run(["docker-compose", "down"], cwd=dir_path, check=True)
        subprocess.run(["docker-compose", "up", "-d"], cwd=dir_path, check=True)
        print(f"Hard restart completed successfully in: {dir_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error during hard restart in {dir_path}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Restart docker-compose services in subdirectories."
    )
    parser.add_argument(
        "parent_directory",
        help="Path to the parent directory containing docker-compose projects"
    )
    parser.add_argument(
        "--only",
        nargs="+",
        help="Restart only the specified subdirectories (by name)"
    )
    args = parser.parse_args()

    parent_directory = args.parent_directory

    if not os.path.isdir(parent_directory):
        print(f"Error: {parent_directory} is not a valid directory.")
        sys.exit(1)

    for dir_entry in os.scandir(parent_directory):
        if dir_entry.is_dir():
            dir_path = dir_entry.path
            dir_name = os.path.basename(dir_path)
            print(f"Checking directory: {dir_path}")

            docker_compose_file = os.path.join(dir_path, "docker-compose.yml")

            if os.path.isfile(docker_compose_file):
                if args.only and dir_name not in args.only:
                    print(f"Skipping {dir_name} (not in --only list).")
                    continue
                print(f"Performing normal restart in {dir_name}...")
                hard_restart_docker_services(dir_path)
            else:
                print(f"No docker-compose.yml found in {dir_path}. Skipping.")


if __name__ == "__main__":
    main()
