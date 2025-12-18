# filter_plugins/xwiki_filters.py
from __future__ import annotations

import re
from typing import Any, Iterable

try:
    # Ansible provides this; don't hard-depend at import time for unit tests
    from ansible.errors import AnsibleFilterError
except Exception:  # pragma: no cover

    class AnsibleFilterError(Exception):
        pass

def _join_elements(elems: Iterable[Any]) -> str:
    return "/".join(str(x) for x in elems)


def xwiki_extension_status(raw: str) -> int:
    """
    Parse the output of the Groovy CheckExtension page.

    - Strips HTML tags and entities (&nbsp;)
    - Returns 200 if extension is INSTALLED, otherwise 404

    Args:
        raw: Raw HTTP body from the checker page.

    Returns:
        200 if installed, 404 if missing/unknown.
    """
    if raw is None:
        return 404

    text = re.sub(r"<[^>]+>", "", str(raw))
    text = text.replace("&nbsp;", " ").replace("\u00a0", " ")
    text = text.strip()

    if text.startswith("INSTALLED::"):
        return 200
    return 404


class FilterModule(object):
    """Custom filters for XWiki helpers."""

    def filters(self):
        return {
            "xwiki_extension_status": xwiki_extension_status,
        }
