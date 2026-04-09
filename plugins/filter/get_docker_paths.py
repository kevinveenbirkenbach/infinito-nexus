# filter_plugins/get_docker_paths.py
from utils.docker.paths_utils import get_docker_paths


class FilterModule(object):
    def filters(self):
        return {
            "get_docker_paths": get_docker_paths,
        }
