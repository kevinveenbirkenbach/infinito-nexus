from ansible.errors import AnsibleFilterError
import copy

def append_csp_hash(applications, application_id, code_one_liner):
    """
    Ensures that applications[application_id].csp.hashes['script-src-elem']
    exists and appends the given one-liner (if not already present).
    """
    if not isinstance(applications, dict):
        raise AnsibleFilterError("`applications` must be a dict")
    if application_id not in applications:
        raise AnsibleFilterError(f"Unknown application_id: {application_id}")

    apps = copy.deepcopy(applications)
    app = apps[application_id]
    server = app.setdefault('server', {})
    csp = server.setdefault('csp', {})
    hashes = csp.setdefault('hashes', {})

    existing = hashes.get('script-src-elem', [])
    if code_one_liner not in existing:
        existing.append(code_one_liner)
    hashes['script-src-elem'] = existing

    return apps

class FilterModule(object):
    def filters(self):
        return {
            'append_csp_hash': append_csp_hash
        }
