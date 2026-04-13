from __future__ import annotations

import re

from ansible.errors import AnsibleFilterError


def image_version(tag: str) -> str:
    """Extract the bare semver from an image tag.

    Strips a leading ``v`` and a trailing distro suffix (e.g. ``-noble``).

    Examples::

        image_version("v1.59.1-noble")  -> "1.59.1"
        image_version("v2.0.0")         -> "2.0.0"
        image_version("1.2.3-jammy")    -> "1.2.3"
    """
    if not isinstance(tag, str):
        raise AnsibleFilterError(
            f"image_version: expected a string, got {type(tag).__name__!r}"
        )
    return re.sub(r"-[^-]+$", "", re.sub(r"^v", "", tag))


class FilterModule:
    def filters(self) -> dict:
        return {"image_version": image_version}
