from __future__ import annotations
from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError
import os


class LookupModule(LookupBase):
    """
    Return a cache-busting string based on the LOCAL file's mtime.

    Usage (single path → string via Jinja):
      {{ lookup('local_mtime_qs', '/path/to/file.css') }}
      -> "?version=1712323456"

    Options:
      param (str): query parameter name (default: "version")
      mode  (str): "qs" (default) → returns "?<param>=<mtime>"
                   "epoch"        → returns "<mtime>"

    Multiple paths (returns list, one result per term):
      {{ lookup('local_mtime_qs', '/a.js', '/b.js', param='v') }}
    """

    def run(self, terms, variables=None, **kwargs):
        if not terms:
            return []

        param = kwargs.get("param", "version")
        mode = kwargs.get("mode", "qs")

        if mode not in ("qs", "epoch"):
            raise AnsibleError("local_mtime_qs: 'mode' must be 'qs' or 'epoch'")

        results = []
        for term in terms:
            path = os.path.abspath(os.path.expanduser(str(term)))

            # Fail fast if path is missing or not a regular file
            if not os.path.exists(path):
                raise AnsibleError(f"local_mtime_qs: file does not exist: {path}")
            if not os.path.isfile(path):
                raise AnsibleError(f"local_mtime_qs: not a regular file: {path}")

            try:
                mtime = int(os.stat(path).st_mtime)
            except OSError as e:
                raise AnsibleError(f"local_mtime_qs: cannot stat '{path}': {e}")

            if mode == "qs":
                results.append(f"?{param}={mtime}")
            else:  # mode == 'epoch'
                results.append(str(mtime))

        return results
