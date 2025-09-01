import datetime
import os

def cdn_paths(cdn_root, application_id, version):
    """
    Build a structured dictionary of all CDN paths for a given application.

    Args:
        cdn_root (str): Base CDN root, e.g. /var/www/cdn
        application_id (str): Role/application identifier
        version (str): Release version string (default: current UTC timestamp)

    Returns:
        dict: Hierarchical CDN path structure
    """
    cdn_root = os.path.abspath(cdn_root)

    return {
        "root": cdn_root,
        "shared": {
            "root": os.path.join(cdn_root, "_shared"),
            "css": os.path.join(cdn_root, "_shared", "css"),
            "js": os.path.join(cdn_root, "_shared", "js"),
            "img": os.path.join(cdn_root, "_shared", "img"),
            "fonts": os.path.join(cdn_root, "_shared", "fonts"),
        },
        "vendor": os.path.join(cdn_root, "vendor"),
        "role": {
            "id": application_id,
            "root": os.path.join(cdn_root, "roles", application_id),
            "version": version,
            "release": {
                "root": os.path.join(cdn_root, "roles", application_id, version),
                "css": os.path.join(cdn_root, "roles", application_id, version, "css"),
                "js": os.path.join(cdn_root, "roles", application_id, version, "js"),
                "img": os.path.join(cdn_root, "roles", application_id, version, "img"),
                "fonts": os.path.join(cdn_root, "roles", application_id, version, "fonts"),
            },
        },
    }

class FilterModule(object):
    def filters(self):
        return {
            "cdn_paths": cdn_paths,
        }
