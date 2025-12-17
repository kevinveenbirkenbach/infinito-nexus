# filter_plugins/cdn_urls.py
import os


def _to_url_tree(obj, cdn_root, base_url):
    """
    Recursively walk a nested dict and replace any string paths under cdn_root
    with URLs based on base_url. Non-path strings (e.g. role.id, role.version)
    are left untouched.
    """
    if isinstance(obj, dict):
        return {k: _to_url_tree(v, cdn_root, base_url) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_to_url_tree(v, cdn_root, base_url) for v in obj]

    if isinstance(obj, str):
        # Normalize inputs
        norm_root = os.path.abspath(cdn_root)
        norm_val = os.path.abspath(obj)

        if norm_val.startswith(norm_root):
            # Compute path relative to CDN root and map to URL
            rel = os.path.relpath(norm_val, norm_root)
            # Handle root itself ('.') → empty path
            if rel == ".":
                rel = ""
            # Always forward slashes for URLs
            rel_url = rel.replace(os.sep, "/")
            base = base_url.rstrip("/")
            return f"{base}/{rel_url}" if rel_url else f"{base}/"
        # Non-CDN string → leave as-is (e.g., role.id / role.version)
        return obj

    # Any other type → return as-is
    return obj


def cdn_urls(cdn_dict, base_url):
    """
    Create a URL-structured dict from a CDN path dict.

    Args:
        cdn_dict (dict): output of cdn_paths(...), containing absolute paths
        base_url (str): CDN base URL, e.g. https://cdn.example.com

    Returns:
        dict: same shape as cdn_dict, but with URLs instead of filesystem paths
              for any strings pointing under cdn_dict['root'].
              Keys like role.id and role.version remain strings as-is.
    """
    if not isinstance(cdn_dict, dict) or "root" not in cdn_dict:
        raise ValueError("cdn_urls expects a dict from cdn_paths with a 'root' key")
    return _to_url_tree(cdn_dict, cdn_dict["root"], base_url)


class FilterModule(object):
    def filters(self):
        return {
            "cdn_urls": cdn_urls,
        }
