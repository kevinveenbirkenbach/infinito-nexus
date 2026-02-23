#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r"""
---
module: file_has_content
short_description: Check if a file exists and has non-empty content
description:
  - Checks whether a file exists on the target host and contains non-whitespace content.
options:
  path:
    description:
      - Path to the file on the target host.
    required: true
    type: str
author:
  - Kevin Veen-Birkenbach
"""

EXAMPLES = r"""
- name: Check if databases.csv has content
  file_has_content:
    path: /etc/infinito/secrets/databases.csv
  register: db_file
"""

RETURN = r"""
exists:
  description: Whether the file exists.
  type: bool
  returned: always
has_content:
  description: Whether the file contains non-empty content.
  type: bool
  returned: always
size:
  description: File size in bytes.
  type: int
  returned: always
"""


def run_module() -> None:
    module_args = dict(
        path=dict(type="str", required=True),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    path = module.params["path"]

    result = {
        "changed": False,
        "exists": False,
        "has_content": False,
        "size": 0,
    }

    if not os.path.exists(path):
        module.fail_json(msg=f"File does not exist: {path}", **result)

    if not os.path.isfile(path):
        module.fail_json(msg=f"Path exists but is not a file: {path}", **result)

    result["exists"] = True
    result["size"] = os.path.getsize(path)

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().strip()
            result["has_content"] = bool(content)
    except Exception as exc:
        module.fail_json(msg=f"Failed to read file: {path}: {exc}", **result)

    module.exit_json(**result)


def main() -> None:
    run_module()


if __name__ == "__main__":
    main()
