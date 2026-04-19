"""Unit tests for patch_decidim.py"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'files'))

from patch_decidim import patch_secrets_yml, patch_omniauth_rb, patch_omniauth_helper_rb


SECRETS_YML_FIXTURE = """\
default: &default
  omniauth:
    google_oauth2:
      enabled: false
      client_secret: <%= ENV["OMNIAUTH_GOOGLE_CLIENT_SECRET"] %>
development:
  <<: *default
  omniauth:
    developer:
      enabled: true
      icon: phone-line
"""

OMNIAUTH_RB_FIXTURE = """\
Decidim::Auth.setup do |config|
  config.providers = []
  end
end
"""

OMNIAUTH_HELPER_FIXTURE = """\
module Decidim
  module OmniauthHelper
    def oauth_icon(provider)
      info = current_organization.enabled_omniauth_providers[provider.to_sym]
    end
  end
end
"""


def test_patch_secrets_yml_adds_oidc_to_default():
    result = patch_secrets_yml(SECRETS_YML_FIXTURE)
    assert "openid_connect:" in result
    assert "OIDC_ENABLED" in result
    assert "OIDC_CLIENT_ID" in result


def test_patch_secrets_yml_adds_oidc_to_development():
    result = patch_secrets_yml(SECRETS_YML_FIXTURE)
    lines = result.split('\n')
    dev_idx = next(i for i, line in enumerate(lines) if 'developer:' in line)
    after_dev = '\n'.join(lines[dev_idx:dev_idx + 20])
    assert "openid_connect:" in after_dev


def test_patch_secrets_yml_is_idempotent():
    result1 = patch_secrets_yml(SECRETS_YML_FIXTURE)
    result2 = patch_secrets_yml(result1)
    assert result1 == result2


def test_patch_omniauth_rb_inserts_provider():
    result = patch_omniauth_rb(OMNIAUTH_RB_FIXTURE)
    assert "omniauth_config[:openid_connect]" in result
    assert "omniauth_openid_connect" in result
    assert "redirect_uri" in result


def test_patch_omniauth_rb_closes_correctly():
    result = patch_omniauth_rb(OMNIAUTH_RB_FIXTURE)
    assert result.rstrip().endswith("end")


def test_patch_omniauth_helper_rb_adds_early_return():
    result = patch_omniauth_helper_rb(OMNIAUTH_HELPER_FIXTURE)
    assert 'return icon("login-box-line") if provider.to_sym == :openid_connect' in result


def test_patch_omniauth_helper_rb_preserves_original_method():
    result = patch_omniauth_helper_rb(OMNIAUTH_HELPER_FIXTURE)
    assert "current_organization.enabled_omniauth_providers" in result
