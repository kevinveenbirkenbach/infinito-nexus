"""
Ansible filter plugin that safely joins URL components from a list.
- Requires a valid '<scheme>://' in the first element (any RFC-3986-ish scheme)
- Preserves the double slash after the scheme, collapses other duplicate slashes
- Raises specific AnsibleFilterError messages for common misuse
"""

import re
from ansible.errors import AnsibleFilterError

_SCHEME_RE = re.compile(r'^([a-zA-Z][a-zA-Z0-9+.\-]*://)(.*)$')

def _to_str_or_error(obj, index):
    """Cast to str, raising a specific AnsibleFilterError with index context."""
    try:
        return str(obj)
    except Exception as e:
        raise AnsibleFilterError(
            f"url_join: unable to convert part at index {index} to string: {e}"
        )

def url_join(parts):
    """
    Join a list of URL parts, URL-aware.

    Args:
        parts (list): List/tuple of URL segments. First element MUST include '<scheme>://'.

    Returns:
        str: Joined URL.

    Raises (all via AnsibleFilterError with specific messages):
        - Input is None/empty
        - Input is not a list/tuple
        - First element missing/invalid scheme
        - Part cannot be converted to string (includes index)
        - Additional scheme found in a later element
    """
    # Basic input validation
    if parts is None:
        raise AnsibleFilterError("url_join: parts must be a non-empty list; got None")
    if not isinstance(parts, (list, tuple)):
        raise AnsibleFilterError(
            f"url_join: parts must be a list/tuple; got {type(parts).__name__}"
        )
    if len(parts) == 0:
        raise AnsibleFilterError("url_join: parts must be a non-empty list")

    # First element must carry the scheme
    first_raw = parts[0]
    if first_raw is None:
        raise AnsibleFilterError(
            "url_join: first element must include a scheme like 'https://'; got None"
        )

    first_str = _to_str_or_error(first_raw, 0)
    m = _SCHEME_RE.match(first_str)
    if not m:
        raise AnsibleFilterError(
            "url_join: first element must start with '<scheme>://', e.g. 'https://example.com'; "
            f"got '{first_str}'"
        )

    scheme = m.group(1)                    # e.g., 'https://', 'ftp://', 'myapp+v1://'
    after_scheme = m.group(2).lstrip('/')  # strip only leading slashes right after scheme

    # Normalize all parts to strings (with index-aware errors)
    normalized = []
    for i, p in enumerate(parts):
        if p is None:
            # Skip None parts silently (like path_join behavior)
            continue
        s = _to_str_or_error(p, i)
        if i > 0 and "://" in s:
            raise AnsibleFilterError(
                f"url_join: only the first element may contain a scheme; part at index {i} "
                f"looks like a URL with scheme ('{s}')."
            )
        normalized.append(s)

    # Replace first element with remainder after scheme
    if normalized:
        normalized[0] = after_scheme
    else:
        # This can only happen if all parts were None, but we gated that earlier
        return scheme

    # Strip slashes at both ends of each part, then filter out empties
    stripped = [p.strip('/') for p in normalized]
    stripped = [p for p in stripped if p != '']

    # If everything is empty after stripping, return just the scheme
    if not stripped:
        return scheme

    return scheme + "/".join(stripped)


class FilterModule(object):
    def filters(self):
        return {
            'url_join': url_join,
        }
