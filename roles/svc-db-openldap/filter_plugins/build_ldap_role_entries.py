def build_ldap_role_entries(applications, users, ldap, group_names=None):
    """Build structured LDAP role entries for the RBAC groups container.

    For every application in ``applications`` that is deployed on the
    current host (its ``application_id`` appears in ``group_names``), emit
    one LDAP group per role declared under ``rbac.roles`` plus an implicit
    ``administrator`` group. The gate exists so the provisioning only
    touches groups for applications that are actually present on the
    host, not every application in the merged config.

    Supports objectClasses: posixGroup (adds gidNumber, memberUid) and
    groupOfNames (adds member).

    Args:
        applications: The merged applications mapping (from
            ``lookup('applications')``).
        users: The merged users mapping (from ``lookup('users')``).
        ldap: The global LDAP configuration (from ``group_vars``).
        group_names: Ansible's ``group_names`` fact for the current host.
            When a list (including an empty list), only applications
            whose ``application_id`` appears in it contribute groups.
            When ``None``, no gating is applied and every application
            contributes — this preserves backwards-compatible behavior
            for unit tests and for any caller that hasn't been migrated
            yet. Production templates MUST pass the live fact.

    Returns:
        dict: ``{dn: entry}`` mapping for every resolved group.
    """

    result = {}

    placeholder_dn = ldap.get("RBAC", {}).get("EMPTY_MEMBER_DN")

    # When group_names is supplied (even as an empty list), filter strictly;
    # when it is None, fall through and include every application.
    if group_names is not None:
        deployed_apps = {
            app_id: cfg for app_id, cfg in applications.items() if app_id in group_names
        }
    else:
        deployed_apps = applications

    for application_id, application_config in deployed_apps.items():
        base_roles = application_config.get("rbac", {}).get("roles", {})
        roles = {
            **base_roles,
            "administrator": {
                "description": "Has full administrative access: manage themes, plugins, settings, and users"
            },
        }

        group_id = application_config.get("group_id")
        user_dn_base = ldap["DN"]["OU"]["USERS"]
        ldap_user_attr = ldap["USER"]["ATTRIBUTES"]["ID"]
        role_dn_base = ldap["DN"]["OU"]["ROLES"]
        flavors = ldap.get("RBAC").get("FLAVORS")

        for role_name, role_conf in roles.items():
            group_cn = f"{application_id}-{role_name}"
            dn = f"cn={group_cn},{role_dn_base}"

            entry = {
                "dn": dn,
                "cn": group_cn,
                "description": role_conf.get("description", ""),
                "objectClass": ["top"] + flavors,
            }

            # Initialize member lists
            member_dns = []
            member_uids = []

            for username, user_config in users.items():
                if role_name in user_config.get("roles", []):
                    user_dn = f"{ldap_user_attr}={username},{user_dn_base}"
                    member_dns.append(user_dn)
                    member_uids.append(username)

            # Add gidNumber for posixGroup
            if "posixGroup" in flavors:
                entry["gidNumber"] = group_id
                if member_uids:
                    entry["memberUid"] = member_uids

            if "groupOfNames" in flavors:
                if member_dns:
                    entry["member"] = member_dns
                else:
                    if not placeholder_dn:
                        raise ValueError(
                            "LDAP.RBAC.EMPTY_MEMBER_DN must be defined when using groupOfNames"
                        )
                    entry["member"] = [placeholder_dn]

            result[dn] = entry

    return result


class FilterModule(object):
    def filters(self):
        return {"build_ldap_role_entries": build_ldap_role_entries}
