# -*- coding: utf-8 -*-
# Part of Infinito.Nexus. See LICENSE file for full copyright and licensing details.

import logging
import os

from odoo import api, models

_logger = logging.getLogger(__name__)

# Configurable OIDC UID field via environment variable
# Defaults to 'preferred_username' which is the standard OIDC claim
# Set via ODOO_OIDC_UID_FIELD env var, sourced from OIDC.ATTRIBUTES.USERNAME
OIDC_UID_FIELD = os.environ.get("ODOO_OIDC_UID_FIELD", "preferred_username")


class ResUsersOAuthConfigurableUid(models.Model):
    """
    Override OAuth user authentication to use a configurable UID claim.

    Odoo's standard auth_oauth module uses the 'user_id' claim from the OAuth
    provider's userinfo response to identify users. However, this claim is not
    standard in OIDC - Keycloak maps the internal UUID as user_id by default.

    This override changes the lookup to use a configurable claim field
    (default: 'preferred_username'), set via the ODOO_OIDC_UID_FIELD env var.
    This aligns Odoo with how other applications in the infinito.nexus stack
    identify users:
    - Mastodon: OIDC_UID_FIELD = preferred_username
    - Pixelfed: PF_OIDC_FIELD_ID = preferred_username
    - EspoCRM: OIDC_USERNAME_CLAIM = preferred_username
    - Taiga: OIDC_USERNAME_CLAIM = preferred_username

    The oauth_uid stored in res_users is now the user's username (e.g., 'admin')
    rather than a UUID, making it human-readable and consistent across the stack.
    """

    _inherit = "res.users"

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """
        Override OAuth signin to use configurable UID field instead of user_id.

        This method is called after OAuth token validation to authenticate
        or create a user. We intercept the validation dict and map the
        configured UID field to 'user_id' so standard Odoo logic continues
        to work while using the correct claim.

        The UID field is configured via ODOO_OIDC_UID_FIELD environment variable,
        which defaults to 'preferred_username'.

        Args:
            provider: OAuth provider ID
            validation: Dict from userinfo endpoint containing user claims
            params: Additional OAuth params (access_token, state, etc.)

        Returns:
            Tuple of (db, login, credential) for session authentication
        """
        # Map configured UID field to user_id if available
        # This allows Odoo's standard logic to find/create users correctly
        if OIDC_UID_FIELD in validation and "user_id" not in validation:
            validation["user_id"] = validation[OIDC_UID_FIELD]
            _logger.debug(
                "OAuth: Using %s '%s' as user_id",
                OIDC_UID_FIELD,
                validation[OIDC_UID_FIELD],
            )

        return super()._auth_oauth_signin(provider, validation, params)
