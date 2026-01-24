#!/usr/bin/python
# roles/web-app-keycloak/library/keycloak_kcadm_update.py

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import subprocess
from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
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
"""

RETURN = r"""
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
"""


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
        # IMPORTANT: kcadm can print JVM warnings before JSON.
        # We decode safely and keep the raw string for later parsing.
        stdout = rc.stdout.decode("utf-8", errors="replace").strip()
        stderr = rc.stderr.decode("utf-8", errors="replace").strip()
        return rc.returncode, stdout, stderr
    except Exception as e:
        module.fail_json(msg="Failed to run kcadm command", cmd=cmd, error=str(e))
        return None, None, None


def parse_json_maybe_noisy(module, text, context=""):
    """
    Keycloak/kcadm can emit JVM warnings to stdout before JSON.
    Some warnings even start with '[' (e.g. "[0.001s][warning]..."), which
    breaks naive "first '[' or '{'" heuristics.

    Deterministic strategy:
      - scan for all occurrences of '{' and '['
      - attempt json.loads() starting from each occurrence (in order)
      - return the first successfully parsed JSON value
      - fail if none work
    """
    if text is None:
        module.fail_json(msg="No output to parse as JSON", context=context)

    s = str(text).lstrip()
    if not s:
        module.fail_json(msg="Empty output; cannot parse JSON", context=context)

    # Collect candidate start positions in order
    candidates = []
    for ch in ("[", "{"):
        start = 0
        while True:
            idx = s.find(ch, start)
            if idx == -1:
                break
            candidates.append(idx)
            start = idx + 1
    candidates = sorted(set(candidates))

    if not candidates:
        module.fail_json(
            msg="No JSON object/array start found in output",
            context=context,
            stdout=text,
        )

    last_err = None
    for idx in candidates:
        chunk = s[idx:].strip()
        try:
            return json.loads(chunk)
        except Exception as e:
            last_err = e
            continue

    # Nothing worked → hard fail with helpful previews
    module.fail_json(
        msg="Failed to parse JSON from output (possibly noisy stdout)",
        context=context,
        error=str(last_err) if last_err else "unknown",
        stdout=text,
        extracted_preview=s[:2000],
    )
    return None


def deep_merge(a, b):
    """Recursive dict merge similar to Ansible's combine(recursive=True)."""
    result = deepcopy(a)
    for k, v in (b or {}).items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


def get_api_and_lookup_field(object_kind, lookup_field):
    if object_kind == "client":
        api = "clients"
        default_lookup = "clientId"
    elif object_kind == "component":
        api = "components"
        default_lookup = "name"
    elif object_kind == "client-scope":
        api = "client-scopes"
        default_lookup = "name"
    elif object_kind == "realm":
        api = "realms"
        default_lookup = "id"
    else:
        api = ""
        default_lookup = ""
    return api, (lookup_field or default_lookup)


def resolve_object_id(
    module, object_kind, api, lookup_field, lookup_value, realm, kcadm_exec
):
    """Return (object_id, exists_flag)."""
    if lookup_field == "id":
        obj_id = str(lookup_value).strip()
        if not obj_id:
            return "", False
        return obj_id, True

    if object_kind == "realm":
        # For realms we treat lookup_value as id/realm name; we will verify on get.
        return str(lookup_value), True

    if object_kind == "client-scope":
        cmd = f"{kcadm_exec} get client-scopes -r {realm} --format json"
        rc, out, _err = run_kcadm(module, cmd, ignore_rc=True)
        if rc != 0 or not out:
            return "", False
        scopes = parse_json_maybe_noisy(
            module, out, context="resolve_object_id: client-scopes"
        )
        for obj in scopes:
            if obj.get(lookup_field) == lookup_value:
                return obj.get("id", ""), True
        return "", False

    # Robust client-side resolution (avoid --query and tolerate noisy stdout)
    if object_kind == "client":
        cmd = f"{kcadm_exec} get clients -r {realm} --format json"
        rc, out, _err = run_kcadm(module, cmd, ignore_rc=True)
        if rc != 0 or not out:
            return "", False
        clients = parse_json_maybe_noisy(
            module, out, context="resolve_object_id: clients"
        )
        for obj in clients:
            if obj.get(lookup_field) == lookup_value:
                return obj.get("id", ""), True
        return "", False

    if object_kind == "component":
        cmd = f"{kcadm_exec} get components -r {realm} --format json"
        rc, out, _err = run_kcadm(module, cmd, ignore_rc=True)
        if rc != 0 or not out:
            return "", False
        comps = parse_json_maybe_noisy(
            module, out, context="resolve_object_id: components"
        )
        for obj in comps:
            if obj.get(lookup_field) == lookup_value:
                return obj.get("id", ""), True
        return "", False

    # Fallback generic (kept for future kinds)
    cmd = (
        f"{kcadm_exec} get {api} -r {realm} "
        f"--query '{lookup_field}={lookup_value}' "
        f"--fields id --format json"
    )
    rc, out, _err = run_kcadm(module, cmd, ignore_rc=True)
    if rc != 0 or not out:
        return "", False

    data = parse_json_maybe_noisy(module, out, context="resolve_object_id: generic")
    if not data:
        return "", False
    return data[0].get("id", ""), True


def get_current_object(module, object_kind, api, object_id, realm, kcadm_exec):
    if object_kind == "realm":
        cmd = f"{kcadm_exec} get {api}/{object_id} --format json"
    else:
        cmd = f"{kcadm_exec} get {api}/{object_id} -r {realm} --format json"
    rc, out, _err = run_kcadm(module, cmd)
    return parse_json_maybe_noisy(
        module, out, context=f"get_current_object: {api}/{object_id}"
    )


def send_update(module, object_kind, api, object_id, realm, kcadm_exec, payload):
    payload_json = json.dumps(payload)
    if object_kind == "realm":
        cmd = (
            f"cat <<'JSON' | {kcadm_exec} update {api}/{object_id} -f -\n"
            f"{payload_json}\nJSON"
        )
    else:
        cmd = (
            f"cat <<'JSON' | {kcadm_exec} update {api}/{object_id} -r {realm} -f -\n"
            f"{payload_json}\nJSON"
        )
    rc, out, err = run_kcadm(module, cmd, ignore_rc=True)
    return rc, out, err


def send_create(module, object_kind, api, realm, kcadm_exec, payload):
    payload_json = json.dumps(payload)
    if object_kind == "realm":
        cmd = f"cat <<'JSON' | {kcadm_exec} create {api} -f -\n{payload_json}\nJSON"
    else:
        cmd = (
            f"cat <<'JSON' | {kcadm_exec} create {api} -r {realm} -f -\n"
            f"{payload_json}\nJSON"
        )
    rc, out, err = run_kcadm(module, cmd, ignore_rc=True)
    return rc, out, err


def run_module():
    module_args = dict(
        object_kind=dict(type="str", required=True),
        lookup_value=dict(type="str", required=True),
        desired=dict(type="dict", required=True),
        lookup_field=dict(type="str", required=False, default=None),
        merge_path=dict(type="str", required=False, default=None),
        force_attrs=dict(type="dict", required=False, default=None),
        kcadm_exec=dict(type="str", required=True),
        realm=dict(type="str", required=False, default=None),
        assert_mode=dict(type="bool", required=False, default=True),
    )

    result = dict(
        changed=False,
        object_exists=False,
        object_id="",
        result={},
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)

    object_kind = module.params["object_kind"]
    lookup_value = module.params["lookup_value"]
    desired = module.params["desired"] or {}
    lookup_field = module.params["lookup_field"]
    merge_path = module.params["merge_path"]
    force_attrs = module.params["force_attrs"] or {}
    kcadm_exec = module.params["kcadm_exec"]
    realm = module.params["realm"]
    assert_mode = module.params["assert_mode"]

    if object_kind != "realm" and not realm:
        module.fail_json(msg="Parameter 'realm' is required for non-realm objects.")

    api, eff_lookup_field = get_api_and_lookup_field(object_kind, lookup_field)
    if not api:
        module.fail_json(msg="Unsupported object_kind", object_kind=object_kind)

    object_id, exists = resolve_object_id(
        module, object_kind, api, eff_lookup_field, lookup_value, realm, kcadm_exec
    )

    result["object_exists"] = exists
    result["object_id"] = object_id

    # --------------------------------------------------------------
    # CREATE PATH (no existing object)
    # If create fails with "already exists", re-resolve and fall
    # through into UPDATE path.
    # --------------------------------------------------------------
    if not exists or not object_id:
        desired_obj = deepcopy(desired)

        if object_kind == "component":
            desired_obj.pop("subComponents", None)

        if force_attrs:
            desired_obj = deep_merge(desired_obj, force_attrs)

        rc, out, err = send_create(
            module, object_kind, api, realm, kcadm_exec, desired_obj
        )

        if rc != 0:
            err_l = (err or "").lower()
            already_exists_markers = ["already exists", "exists with same", "conflict"]
            if any(m in err_l for m in already_exists_markers):
                # Lookup likely failed; re-resolve id and continue as update.
                object_id2, exists2 = resolve_object_id(
                    module,
                    object_kind,
                    api,
                    eff_lookup_field,
                    lookup_value,
                    realm,
                    kcadm_exec,
                )
                if exists2 and object_id2:
                    object_id = object_id2
                    exists = True
                    result["object_exists"] = True
                    result["object_id"] = object_id
                else:
                    module.fail_json(
                        msg="Create failed with 'already exists' but re-resolve did not find object id",
                        rc=rc,
                        stdout=out,
                        stderr=err,
                        payload=desired_obj,
                    )
            else:
                module.fail_json(
                    msg="Failed to create Keycloak object",
                    rc=rc,
                    stdout=out,
                    stderr=err,
                    payload=desired_obj,
                )

        # If create succeeded, we are done.
        if not exists or not object_id:
            result["changed"] = True
            result["result"] = desired_obj
            module.exit_json(**result)

    # --------------------------------------------------------------
    # UPDATE PATH (object exists)
    # --------------------------------------------------------------
    cur_obj = get_current_object(module, object_kind, api, object_id, realm, kcadm_exec)

    # Optional safety check: providerId must match for components
    if assert_mode and object_kind == "component":
        cur_provider = cur_obj.get("providerId", "")
        des_provider = desired.get("providerId", "")
        if cur_provider and des_provider and cur_provider != des_provider:
            module.fail_json(
                msg="Refusing to update component due to providerId mismatch",
                current_providerId=cur_provider,
                desired_providerId=des_provider,
            )

    # Build merge payload (full or subpath)
    if merge_path:
        merge_payload = {merge_path: deepcopy(desired.get(merge_path, {}))}
    else:
        merge_payload = deepcopy(desired)

    desired_obj = deep_merge(cur_obj, merge_payload)

    # Preserve immutable fields
    if object_kind == "client":
        for k in ["id", "clientId"]:
            if k in cur_obj:
                desired_obj[k] = cur_obj[k]

    elif object_kind == "component":
        for k in ["id", "providerId", "providerType", "parentId"]:
            if k in cur_obj:
                desired_obj[k] = cur_obj[k]
        desired_obj.pop("subComponents", None)

    elif object_kind == "client-scope":
        for k in ["id", "name"]:
            if k in cur_obj:
                desired_obj[k] = cur_obj[k]

    elif object_kind == "realm":
        for k in ["id", "realm"]:
            if k in cur_obj:
                desired_obj[k] = cur_obj[k]

    # Apply forced attributes (last)
    if force_attrs:
        desired_obj = deep_merge(desired_obj, force_attrs)

    # Always send update and rely on Keycloak to no-op.
    rc, out, err = send_update(
        module, object_kind, api, object_id, realm, kcadm_exec, desired_obj
    )
    if rc != 0:
        module.fail_json(
            msg="Failed to update Keycloak object",
            rc=rc,
            stdout=out,
            stderr=err,
            payload=desired_obj,
        )

    result["changed"] = True
    result["result"] = desired_obj
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
