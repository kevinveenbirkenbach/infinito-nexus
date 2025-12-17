import os

def has_env(application_id, base_dir='.'):
    """
    Check if env.j2 exists under roles/{{ application_id }}/templates/env.j2
    """
    path = os.path.join(base_dir, 'roles', application_id, 'templates', 'env.j2')
    return os.path.isfile(path)

class FilterModule(object):
    def filters(self):
        return {
            'has_env': has_env,
        }
