# filter_plugins/xwiki_filters.py
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Iterable
try:
    # Ansible provides this; don't hard-depend at import time for unit tests
    from ansible.errors import AnsibleFilterError
except Exception:  # pragma: no cover
    class AnsibleFilterError(Exception):
        pass


_JOB_LOC_RE = re.compile(r"/rest/jobstatus/([^?\s#]+)")


def _join_elements(elems: Iterable[Any]) -> str:
    return "/".join(str(x) for x in elems)


def xwiki_job_id(response: Any, default: Optional[str] = None, strict: bool = False) -> Optional[str]:
    """
    Extract a XWiki job ID from a typical Ansible `uri` response.

    Supports:
      - JSON mapping: {"id": {"elements": ["install", "extensions", "123"]}}
      - JSON mapping: {"id": "install/extensions/123"}
      - Fallback from Location header or URL containing "/rest/jobstatus/<id>"

    Args:
        response: The registered result from the `uri` task (dict-like).
        default:  Value to return when no ID can be found (if strict=False).
        strict:   If True, raise AnsibleFilterError when no ID is found.

    Returns:
        The job ID string, or `default`/None.

    Raises:
        AnsibleFilterError: if `strict=True` and no job ID can be determined.
    """
    if not isinstance(response, dict):
        if strict:
            raise AnsibleFilterError("xwiki_job_id: response must be a dict-like Ansible result.")
        return default

    # 1) Try JSON body
    j = response.get("json")
    if isinstance(j, dict):
        job_id = j.get("id")
        if isinstance(job_id, dict):
            elems = job_id.get("elements")
            if isinstance(elems, list) and elems:
                return _join_elements(elems)
        if isinstance(job_id, str) and job_id.strip():
            return job_id.strip()

    # 2) Fallback: Location header (Ansible `uri` exposes it as `location`)
    loc = response.get("location")
    if isinstance(loc, str) and loc:
        m = _JOB_LOC_RE.search(loc)
        if m:
            return m.group(1)

    # 3) As a last resort, try the final `url` (in case server redirected and Ansible captured it)
    url = response.get("url")
    if isinstance(url, str) and url:
        m = _JOB_LOC_RE.search(url)
        if m:
            return m.group(1)

    # Not found
    if strict:
        raise AnsibleFilterError("xwiki_job_id: could not extract job ID from response.")
    return default


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
    text = text.replace("&nbsp;", " ").replace("\u00A0", " ")
    text = text.strip()

    if text.startswith("INSTALLED::"):
        return 200
    return 404


class FilterModule(object):
    """Custom filters for XWiki helpers."""
    def filters(self):
        return {
            "xwiki_job_id": xwiki_job_id,
            "xwiki_extension_status": xwiki_extension_status,
        }
