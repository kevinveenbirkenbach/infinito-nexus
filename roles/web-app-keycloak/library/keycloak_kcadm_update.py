#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
import json
import subprocess
from copy import deepcopy

DOCUMENTATION = r'''
---
module: keycloak_kcadm_update

short_description: Create or update Keycloak clients/components/client-scopes/realms via kcadm.

description:
  - Generic "create or update" module for Keycloak objects using kcadm.
  - Resolves the object by a lookup field, reads current state if it exists,
    deep-merges the desired state on top (optionally only a sub-path),
    preserves immutable fields, applies forced attributes and then
    updates or creates the object.

options:
  object_kind:
    description: Kind of the Keycloak object.
    type: str
    required: True
    choices: [client, component, client-scope, realm]
  lookup_value:
    description: Value to look up the object (e.g. clientId, component name, realm id).
    type: str
    required: True
  desired:
    description: Desired object dictionary.
    type: dict
    required: True
  lookup_field:
    description:
      - Lookup field name.
      - Defaults depend on object_kind:
      - client -> clientId
      - component -> name
      - client-scope -> name
      - realm -> id
    type: str
    required: False
  merge_path:
    description:
      - If set (e.g. C(config)), only this subkey is merged into the current object.
      - If omitted, the whole object is merged.
    type: str
    required: False
  force_attrs:
    description:
      - Attributes that are always applied last on the final payload.
    type: dict
    required: False
  kcadm_exec:
    description:
      - Command to execute kcadm.
      - E.g. C(docker exec -i keycloak /opt/keycloak/bin/kcadm.sh).
    type: str
    required: True
  realm:
    description:
      - Realm name used for non-realm objects.
    type: str
    required: False
  assert_mode:
    description:
      - If true, additional safety checks are applied (e.g. providerId match for components).
    type: bool
    required: False
    default: True

author:
  - Your Name
'''

EXAMPLES = r'''
- name: Create or update a Keycloak client (merge full object)
  keycloak_kcadm_update:
    object_kind: client
    lookup_value: "{{ KEYCLOAK_CLIENT_ID }}"
    desired: "{{ KEYCLOAK_DICTIONARY_CLIENT }}"
    kcadm_exec: "{{ KEYCLOAK_EXEC_KCADM }}"
    realm: "{{ KEYCLOAK_REALM }}"

- name: Create or update LDAP component (merge only config)
  keycloak_kcadm_update:
    object_kind: component
    lookup_value: "{{ KEYCLOAK_LDAP_CMP_NAME }}"
    desired: "{{ KEYCLOAK_DICTIONARY_LDAP }}"
    merge_path: config
    kcadm_exec: "{{ KEYCLOAK_EXEC_KCADM }}"
    realm: "{{ KEYCLOAK_REALM }}"
    force_attrs:
      parentId: "{{ KEYCLOAK_REALM }}"
'''

RETURN = r'''
changed:
  description: Whether the object was created or updated.
  type: bool
  returned: always
object_exists:
  description: Whether the object was found by the lookup.
  type: bool
  returned: always
object_id:
  description: Resolved object id (if exists).
  type: str
  returned: always
result:
  description: The final payload that was sent to Keycloak.
  type: dict
  returned: always
'''

def run_kcadm(module, cmd, ignore_rc=False):
    """Run a shell command for kcadm."""
    try:
        rc = subprocess.run(
            cmd,
            shell=True,
            check=not ignore_rc,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout = rc.stdout.decode('utf-8').strip()
        stderr = rc.stderr.decode('utf-8').strip()
        return rc.returncode, stdout, stderr
    except Exception as e:
        module.fail_json(msg="Failed to run kcadm command", cmd=cmd, error=str(e))


def deep_merge(a, b):
    """Recursive dict merge similar to Ansible's combine(recursive=True)."""
    result = deepcopy(a)
    for k, v in b.items():
        if (
            k in result
            and isinstance(result[k], dict)
            and isinstance(v, dict)
        ):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


def get_api_and_lookup_field(object_kind, lookup_field):
    if object_kind == 'client':
        api = 'clients'
        default_lookup = 'clientId'
    elif object_kind == 'component':
        api = 'components'
        default_lookup = 'name'
    elif object_kind == 'client-scope':
        api = 'client-scopes'
        default_lookup = 'name'
    elif object_kind == 'realm':
        api = 'realms'
        default_lookup = 'id'
    else:
        api = ''
        default_lookup = ''
    return api, (lookup_field or default_lookup)


def resolve_object_id(module, object_kind, api, lookup_field, lookup_value, realm, kcadm_exec):
    """Return (object_id, exists_flag)."""
    if lookup_field == 'id':
        obj_id = str(lookup_value).strip()
        if not obj_id:
            return '', False
        return obj_id, True

    if object_kind == 'realm':
        # For realms we treat lookup_value as id/realm name; we will verify on get.
        return str(lookup_value), True

    if object_kind == 'client-scope':
        cmd = f"{kcadm_exec} get client-scopes -r {realm} --format json"
        rc, out, err = run_kcadm(module, cmd, ignore_rc=True)
        if rc != 0 or not out:
            return '', False
        try:
            scopes = json.loads(out)
        except Exception:
            return '', False
        for obj in scopes:
            if obj.get(lookup_field) == lookup_value:
                return obj.get('id', ''), True
        return '', False

    # Generic path (client, component via query)
    cmd = (
        f"{kcadm_exec} get {api} -r {realm} "
        f"--query '{lookup_field}={lookup_value}' "
        f"--fields id --format json"
    )
    rc, out, err = run_kcadm(module, cmd, ignore_rc=True)
    if rc != 0 or not out:
        return '', False
    try:
        data = json.loads(out)
        if not data:
            return '', False
        return data[0].get('id', ''), True
    except Exception:
        return '', False


def get_current_object(module, object_kind, api, object_id, realm, kcadm_exec):
    if object_kind == 'realm':
        cmd = f"{kcadm_exec} get {api}/{object_id} --format json"
    else:
        cmd = f"{kcadm_exec} get {api}/{object_id} -r {realm} --format json"
    rc, out, err = run_kcadm(module, cmd)
    try:
        return json.loads(out)
    except Exception as e:
        module.fail_json(msg="Failed to parse current Keycloak object JSON", error=str(e), stdout=out)


def send_update(module, object_kind, api, object_id, realm, kcadm_exec, payload):
    payload_json = json.dumps(payload)
    if object_kind == 'realm':
        cmd = f"cat <<'JSON' | {kcadm_exec} update {api}/{object_id} -f -\n{payload_json}\nJSON"
    else:
        cmd = f"cat <<'JSON' | {kcadm_exec} update {api}/{object_id} -r {realm} -f -\n{payload_json}\nJSON"
    rc, out, err = run_kcadm(module, cmd, ignore_rc=True)
    return rc, out, err


def send_create(module, object_kind, api, realm, kcadm_exec, payload):
    payload_json = json.dumps(payload)
    if object_kind == 'realm':
        cmd = f"cat <<'JSON' | {kcadm_exec} create {api} -f -\n{payload_json}\nJSON"
    else:
        cmd = f"cat <<'JSON' | {kcadm_exec} create {api} -r {realm} -f -\n{payload_json}\nJSON"
    rc, out, err = run_kcadm(module, cmd, ignore_rc=True)
    return rc, out, err


def run_module():
    module_args = dict(
        object_kind=dict(type='str', required=True),
        lookup_value=dict(type='str', required=True),
        desired=dict(type='dict', required=True),
        lookup_field=dict(type='str', required=False, default=None),
        merge_path=dict(type='str', required=False, default=None),
        force_attrs=dict(type='dict', required=False, default=None),
        kcadm_exec=dict(type='str', required=True),
        realm=dict(type='str', required=False, default=None),
        assert_mode=dict(type='bool', required=False, default=True),
    )

    result = dict(
        changed=False,
        object_exists=False,
        object_id='',
        result={},
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    object_kind = module.params['object_kind']
    lookup_value = module.params['lookup_value']
    desired = module.params['desired'] or {}
    lookup_field = module.params['lookup_field']
    merge_path = module.params['merge_path']
    force_attrs = module.params['force_attrs'] or {}
    kcadm_exec = module.params['kcadm_exec']
    realm = module.params['realm']
    assert_mode = module.params['assert_mode']

    if object_kind != 'realm' and not realm:
        module.fail_json(msg="Parameter 'realm' is required for non-realm objects.")

    api, eff_lookup_field = get_api_and_lookup_field(object_kind, lookup_field)
    if not api:
        module.fail_json(msg="Unsupported object_kind", object_kind=object_kind)

    object_id, exists = resolve_object_id(
        module, object_kind, api, eff_lookup_field, lookup_value, realm, kcadm_exec
    )

    result['object_exists'] = exists
    result['object_id'] = object_id

    # CREATE PATH (no existing object)
    if not exists or not object_id:
        desired_obj = deepcopy(desired)

        # Drop unsupported fields for components (e.g. subComponents)
        if object_kind == 'component':
            desired_obj.pop('subComponents', None)

        # Apply forced attributes (common behavior)
        if force_attrs:
            desired_obj = deep_merge(desired_obj, force_attrs)

        rc, out, err = send_create(
            module, object_kind, api, realm, kcadm_exec, desired_obj
        )
        if rc != 0:
            module.fail_json(
                msg="Failed to create Keycloak object",
                rc=rc, stdout=out, stderr=err, payload=desired_obj
            )

        result['changed'] = True
        result['result'] = desired_obj
        module.exit_json(**result)

    # UPDATE PATH (object exists)
    cur_obj = get_current_object(module, object_kind, api, object_id, realm, kcadm_exec)

    # Optional safety check: providerId must match for components
    if assert_mode and object_kind == 'component':
        cur_provider = cur_obj.get('providerId', '')
        des_provider = desired.get('providerId', '')
        if cur_provider and des_provider and cur_provider != des_provider:
            module.fail_json(
                msg="Refusing to update component due to providerId mismatch",
                current_providerId=cur_provider,
                desired_providerId=des_provider,
            )

    # Build merge payload (full or subpath)
    if merge_path:
        merge_payload = {
            merge_path: deepcopy(desired.get(merge_path, {}))
        }
    else:
        merge_payload = deepcopy(desired)

    desired_obj = deep_merge(cur_obj, merge_payload)

    # Preserve immutable fields
    if object_kind == 'client':
        for k in ['id', 'clientId']:
            if k in cur_obj:
                desired_obj[k] = cur_obj[k]

    elif object_kind == 'component':
        for k in ['id', 'providerId', 'providerType', 'parentId']:
            if k in cur_obj:
                desired_obj[k] = cur_obj[k]
        # Drop unsupported fields such as subComponents
        desired_obj.pop('subComponents', None)

    elif object_kind == 'client-scope':
        for k in ['id', 'name']:
            if k in cur_obj:
                desired_obj[k] = cur_obj[k]

    elif object_kind == 'realm':
        for k in ['id', 'realm']:
            if k in cur_obj:
                desired_obj[k] = cur_obj[k]

    # Apply forced attributes (last)
    if force_attrs:
        desired_obj = deep_merge(desired_obj, force_attrs)

    # If nothing changed logically, we could diff & short-circuit.
    # For simplicity we always send update and rely on Keycloak to no-op.
    rc, out, err = send_update(
        module, object_kind, api, object_id, realm, kcadm_exec, desired_obj
    )
    if rc != 0:
        module.fail_json(
            msg="Failed to update Keycloak object",
            rc=rc, stdout=out, stderr=err, payload=desired_obj
        )

    result['changed'] = True
    result['result'] = desired_obj
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
