#!/usr/bin/env python3
import sys
from pathlib import Path

from ansible.errors import AnsibleFilterError


class FilterModule:
    def filters(self):
        plugin_dir = str(Path(__file__).parent)
        project_root = str(Path(str(Path(plugin_dir) / ".." / "..")).resolve())
        if project_root not in sys.path:
            sys.path.append(project_root)

        try:
            from utils.domains.primary_domain import get_domain
        except ImportError as e:
            raise AnsibleFilterError(
                f"could not import utils.domains.primary_domain: {e}"
            ) from e

        return {"get_domain": get_domain}
