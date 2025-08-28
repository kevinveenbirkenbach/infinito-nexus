def build_ldap_nested_group_entries(applications, users, ldap):
    """
    Builds structured LDAP role entries using the global `ldap` configuration.
    Supports objectClasses: posixGroup (adds gidNumber, memberUid), groupOfNames (adds member).
    Now nests roles under an application-level OU: application-id/role.
    """

    result = {}

    # Base DN components
    role_dn_base = ldap["DN"]["OU"]["ROLES"]
    user_dn_base = ldap["DN"]["OU"]["USERS"]
    ldap_user_attr = ldap["USER"]["ATTRIBUTES"]["ID"]

    # Supported objectClass flavors
    flavors = ldap.get("RBAC").get("FLAVORS")

    for application_id, app_config in applications.items():
        # Compute the DN for the application-level OU
        app_ou_dn = f"ou={application_id},{role_dn_base}"

        ou_entry = {
            "dn": app_ou_dn,
            "objectClass": ["top", "organizationalUnit"],
            "ou": application_id,
            "description": f"Roles for application {application_id}" 
        }
        result[app_ou_dn] = ou_entry

        # Standard roles with an extra 'administrator'
        base_roles = app_config.get("rbac", {}).get("roles", {})
        roles = {
            **base_roles,
            "administrator": {
                "description": "Has full administrative access: manage themes, plugins, settings, and users"
            }
        }

        group_id = app_config.get("group_id")

        for role_name, role_conf in roles.items():
            # Build CN under the application OU
            cn = role_name
            dn = f"cn={cn},{app_ou_dn}"

            entry = {
                "dn": dn,
                "cn": cn,
                "description": role_conf.get("description", ""),
                "objectClass": ["top"] + flavors,
            }

            member_dns = []
            member_uids = []
            for username, user_conf in users.items():
                if role_name in user_conf.get("roles", []):
                    member_dns.append(f"{ldap_user_attr}={username},{user_dn_base}")
                    member_uids.append(username)

            if "posixGroup" in flavors:
                entry["gidNumber"] = group_id
                if member_uids:
                    entry["memberUid"] = member_uids

            if "groupOfNames" in flavors and member_dns:
                entry["member"] = member_dns

            result[dn] = entry

    return result


class FilterModule(object):
    def filters(self):
        return {
            "build_ldap_nested_group_entries": build_ldap_nested_group_entries
        }
