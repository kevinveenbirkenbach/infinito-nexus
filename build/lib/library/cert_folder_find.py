from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.cert_utils import CertUtils

def main():
    module_args = dict(
        domain=dict(type='str', required=True),
        cert_base_path=dict(type='str', required=False, default='/etc/letsencrypt/live'),
        debug=dict(type='bool', required=False, default=False),
    )

    module = AnsibleModule(
        argument_spec=module_args
    )

    domain = module.params['domain']
    cert_base_path = module.params['cert_base_path']
    debug = module.params['debug']

    folder = CertUtils.find_cert_for_domain(domain, cert_base_path, debug)

    if folder is None:
        module.fail_json(msg=f"No certificate covering domain {domain} found.")
    else:
        module.exit_json(folder=folder)

if __name__ == '__main__':
    main()
