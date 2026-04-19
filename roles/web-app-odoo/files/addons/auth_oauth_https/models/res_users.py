# -*- coding: utf-8 -*-
# Part of Infinito.Nexus. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ResUsersOAuthPreferredUsername(models.Model):
    """
    Override OAuth user authentication to use preferred_username claim.

    Odoo's standard auth_oauth module uses the 'user_id' claim from the OAuth
    provider's userinfo response to identify users. However, this claim is not
    standard in OIDC - Keycloak maps the internal UUID as user_id by default.

    This override changes the lookup to use 'preferred_username', which is the
    standard OIDC claim for the user's username. This aligns Odoo with how
    other applications in the infinito.nexus stack identify users:
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
        Override OAuth signin to use preferred_username instead of user_id.

        This method is called after OAuth token validation to authenticate
        or create a user. We intercept the validation dict and map
        'preferred_username' to 'user_id' so standard Odoo logic continues
        to work while using the correct claim.

        Args:
            provider: OAuth provider ID
            validation: Dict from userinfo endpoint containing user claims
            params: Additional OAuth params (access_token, state, etc.)

        Returns:
            Tuple of (db, login, credential) for session authentication
        """
        # Map preferred_username to user_id if available
        # This allows Odoo's standard logic to find/create users correctly
        if "preferred_username" in validation and "user_id" not in validation:
            validation["user_id"] = validation["preferred_username"]
            _logger.debug(
                "OAuth: Using preferred_username '%s' as user_id",
                validation["preferred_username"],
            )

        return super()._auth_oauth_signin(provider, validation, params)
