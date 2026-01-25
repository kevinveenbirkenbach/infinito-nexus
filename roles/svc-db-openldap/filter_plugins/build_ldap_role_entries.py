def build_ldap_role_entries(applications, users, ldap):
    """
    Builds structured LDAP role entries using the global `ldap` configuration.
    Supports objectClasses: posixGroup (adds gidNumber, memberUid), groupOfNames (adds member).
    """

    result = {}

    placeholder_dn = ldap.get("RBAC", {}).get("EMPTY_MEMBER_DN")

    for application_id, application_config in applications.items():
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
