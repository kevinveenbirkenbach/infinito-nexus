from module_utils.entity_name_utils import get_entity_name


def get_docker_paths(application_id: str, path_docker_compose_instances: str) -> dict:
    """
    Build the docker_compose dict based on
    path_docker_compose_instances and application_id.
    Uses get_entity_name to extract the entity name from application_id.
    """
    entity = get_entity_name(application_id)
    base = f"{path_docker_compose_instances}{entity}/"

    return {
        "directories": {
            "instance": base,
            "env": f"{base}.env/",
            "services": f"{base}services/",
            "volumes": f"{base}volumes/",
            "config": f"{base}config/",
        },
        "files": {
            "env": f"{base}.env/env",
            "docker_compose": f"{base}docker-compose.yml",
            "docker_compose_override": f"{base}docker-compose.override.yml",
            "dockerfile": f"{base}Dockerfile",
        },
    }


class FilterModule(object):
    def filters(self):
        return {
            "get_docker_paths": get_docker_paths,
        }
