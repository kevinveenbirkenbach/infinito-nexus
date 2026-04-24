<?php
/**
 * Plugin Name: Infinito.Nexus OIDC RBAC Role Mapper
 * Description: Maps Keycloak groups claim (prefix: web-app-wordpress-)
 *              delivered by daggerhart/openid-connect-generic to a
 *              WordPress role. Installed as a mu-plugin so it is always
 *              active and cannot be deactivated from the admin UI.
 * Version:     1.0.0
 * Author:      Infinito.Nexus
 *
 * Requirement: docs/requirements/004-generic-rbac-ldap-auto-provisioning.md
 *
 * Contract:
 * - Each WordPress user's role is derived purely from the `groups` claim
 *   of the OIDC userinfo response. No direct LDAP bind from WordPress.
 * - The claim is the multivalued group-path claim emitted by the
 *   Keycloak RBAC client scope (see
 *   roles/web-app-keycloak/templates/import/scopes/rbac.json.j2).
 * - Only groups with the prefix `web-app-wordpress-` contribute, so that
 *   group memberships for other apps (e.g. `web-app-discourse-editor`)
 *   are ignored here.
 * - When the user is a member of multiple matching groups, the highest-
 *   privilege role wins (administrator > editor > author > contributor
 *   > subscriber).
 * - When the user is a member of no matching group, the weakest role
 *   `subscriber` is assigned. This is the deterministic fallback.
 */

if (!defined('ABSPATH')) {
    exit;
}

// daggerhart/openid-connect-generic fires this action after every
// successful OIDC sign-in, both for newly-created and existing users.
// We hook both create and update so the role is re-evaluated on every
// login and stays in sync with Keycloak group membership.
add_action('openid-connect-generic-user-create', 'infinito_oidc_map_rbac_role', 10, 2);
add_action(
    'openid-connect-generic-update-user-using-current-claim',
    'infinito_oidc_map_rbac_role',
    10,
    2
);

/**
 * Map OIDC `groups` claim to a WordPress role.
 *
 * @param \WP_User $user       The user whose role is being set.
 * @param array    $user_claim The OIDC claims as delivered by the IDP.
 */
function infinito_oidc_map_rbac_role($user, $user_claim) {
    if (!($user instanceof WP_User)) {
        return;
    }
    if (!is_array($user_claim)) {
        $user->set_role('subscriber');
        return;
    }

    $groups = isset($user_claim['groups']) ? $user_claim['groups'] : array();
    if (!is_array($groups)) {
        $groups = array($groups);
    }

    // Prefix identifying WordPress RBAC groups produced by
    // roles/svc-db-openldap/filter_plugins/build_ldap_role_entries.py.
    // Hard-coded here by design: the mu-plugin is shipped for this
    // specific role, and the prefix is the role's stable contract.
    $prefix = 'web-app-wordpress-';

    // Priority order — higher-privilege role wins when the user is in
    // multiple groups simultaneously.
    $priority = array(
        'administrator',
        'editor',
        'author',
        'contributor',
        'subscriber',
    );

    $matched = array();
    foreach ($groups as $group) {
        if (!is_string($group)) {
            continue;
        }
        // Keycloak's oidc-group-membership-mapper with full.path=true emits
        // paths like `/roles/web-app-wordpress-editor`. Only the final path
        // segment (the LDAP group cn) carries the application_id + role.
        $segments = explode('/', trim($group, '/'));
        $cn = end($segments);
        if (!is_string($cn) || strpos($cn, $prefix) !== 0) {
            continue;
        }
        $role = substr($cn, strlen($prefix));
        if (in_array($role, $priority, true)) {
            $matched[] = $role;
        }
    }

    // Pick the highest-priority match; fall back to subscriber when no
    // RBAC group is attached so an unauthorised login never silently
    // gets elevated rights.
    $selected = 'subscriber';
    foreach ($priority as $role) {
        if (in_array($role, $matched, true)) {
            $selected = $role;
            break;
        }
    }

    $user->set_role($selected);
}
