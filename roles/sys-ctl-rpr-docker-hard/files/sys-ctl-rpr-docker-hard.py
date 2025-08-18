import os
import sys
import subprocess

def restart_docker_services(dir_path):
    """
    Restart docker-compose services in the given directory.
    """
    try:
        print(f"Restarting docker-compose services in: {dir_path}")
        subprocess.run(["docker-compose", "restart"], cwd=dir_path, check=True)
        print(f"Services restarted successfully in: {dir_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error restarting services in {dir_path}: {e}")

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide the path to the parent directory as a parameter.")
        sys.exit(1)

    parent_directory = sys.argv[1]

    for dir_entry in os.scandir(parent_directory):
        if dir_entry.is_dir():
            dir_path = dir_entry.path
            dir_name = os.path.basename(dir_path)
            print(f"Checking directory: {dir_path}")
            
            docker_compose_file = os.path.join(dir_path, "docker-compose.yml")
            
            if os.path.isfile(docker_compose_file):
                print(f"Found docker-compose.yml in {dir_path}.")
                if dir_name == "web-app-mailu":
                    print(f"Directory {dir_name} detected. Performing hard restart...")
                    hard_restart_docker_services(dir_path)
                else:
                    print(f"Restarting services in {dir_path}...")
                    restart_docker_services(dir_path)
            else:
                print(f"No docker-compose.yml found in {dir_path}. Skipping.")
