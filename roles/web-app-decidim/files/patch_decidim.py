"""Patches Decidim gem files to add OpenID Connect support."""
import re


OIDC_BLOCK = """    openid_connect:
      enabled: <%= Decidim::Env.new("OIDC_ENABLED").to_boolean_string %>
      icon: login-box-line
      client_id: <%= ENV["OIDC_CLIENT_ID"] %>
      client_secret: <%= ENV["OIDC_CLIENT_SECRET"] %>
      site: <%= ENV["OIDC_ISSUER"] %>
      issuer: <%= ENV["OIDC_ISSUER"] %>
      discovery: true
      scope: ["openid", "email", "profile"]
"""

OMNIAUTH_INJECTION = r"""
    if omniauth_config[:openid_connect].present?
      require "omniauth_openid_connect"
      ENV["SSL_CERT_FILE"] = ENV["CURL_CA_BUNDLE"] if ENV["CURL_CA_BUNDLE"] && File.exist?(ENV["CURL_CA_BUNDLE"].to_s)
      provider(
        :openid_connect,
        name: :openid_connect,
        scope: [:openid, :email, :profile],
        response_type: :code,
        discovery: true,
        issuer: ENV.fetch("OIDC_ISSUER", nil),
        client_options: {
          host: URI.parse(ENV.fetch("OIDC_ISSUER", "https://auth.infinito.example")).host,
          identifier: ENV.fetch("OIDC_CLIENT_ID", nil),
          secret:     ENV.fetch("OIDC_CLIENT_SECRET", nil),
          redirect_uri: "#{ENV.fetch('APPLICATION_HOST', 'https://decidim.infinito.example').chomp('/')}/users/auth/openid_connect/callback"
        }
      )
    end
"""


def patch_secrets_yml(content: str) -> str:
    """Add openid_connect block to default and development omniauth sections."""
    google_anchor = '      client_secret: <%= ENV["OMNIAUTH_GOOGLE_CLIENT_SECRET"] %>'
    if google_anchor in content and 'openid_connect:' not in content.split(google_anchor)[1].split('    developer:')[0]:
        content = content.replace(
            google_anchor,
            google_anchor + '\n' + OIDC_BLOCK.rstrip()
        )
    developer_anchor = '    developer:\n      enabled: true\n      icon: phone-line'
    if developer_anchor in content and 'openid_connect:' not in content.split(developer_anchor)[1].split('\n\n')[0]:
        content = content.replace(
            developer_anchor,
            developer_anchor + '\n' + OIDC_BLOCK.rstrip()
        )
    return content


def patch_omniauth_rb(content: str) -> str:
    """Insert openid_connect provider registration before the closing end."""
    content = re.sub(r'(  end\nend\s*)$', OMNIAUTH_INJECTION + r'\1', content.rstrip()) + '\n'
    return content


def patch_omniauth_helper_rb(content: str) -> str:
    """Return login-box-line icon for openid_connect to avoid registry lookup failure."""
    return content.replace(
        "    def oauth_icon(provider)",
        '    def oauth_icon(provider)\n      return icon("login-box-line") if provider.to_sym == :openid_connect'
    )


if __name__ == "__main__":
    secrets_path = "/code/config/secrets.yml"
    with open(secrets_path) as f:
        content = f.read()
    with open(secrets_path, "w") as f:
        f.write(patch_secrets_yml(content))
    print("secrets.yml patched")

    omniauth_path = "/usr/local/bundle/gems/decidim-core-0.28.0/config/initializers/omniauth.rb"
    with open(omniauth_path) as f:
        content = f.read()
    with open(omniauth_path, "w") as f:
        f.write(patch_omniauth_rb(content))
    print("omniauth.rb patched")

    helper_path = "/usr/local/bundle/gems/decidim-core-0.28.0/app/helpers/decidim/omniauth_helper.rb"
    with open(helper_path) as f:
        content = f.read()
    with open(helper_path, "w") as f:
        f.write(patch_omniauth_helper_rb(content))
    print("omniauth_helper.rb patched")
