def get_docker_image(applications, application_id, image_key:str=None):
    image_key = image_key if image_key else application_id
    docker = applications.get(application_id, {}).get("docker", {})
    version = docker.get("versions", {}).get(image_key)
    image = docker.get("images", {}).get(image_key)

    if not image:
        raise ValueError(f"Missing image for {application_id}:{image_key}")

    if not version:
        raise ValueError(f"Missing version for {application_id}:{image_key}")
    
    return f"{image}:{version}"

class FilterModule(object):
    def filters(self):
        return {
            'get_docker_image': get_docker_image,
        }
