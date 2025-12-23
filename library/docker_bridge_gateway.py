#!/usr/bin/python
from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule
import subprocess


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip())
    return (p.stdout or "").strip()


def main():
    module = AnsibleModule(
        argument_spec=dict(
            network=dict(type="str", default="bridge"),
        ),
        supports_check_mode=True,
    )

    network = module.params["network"]

    try:
        gw = run(
            [
                "docker",
                "network",
                "inspect",
                network,
                "--format",
                "{{ (index .IPAM.Config 0).Gateway }}",
            ]
        )
        module.exit_json(changed=False, gateway=gw)
    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
