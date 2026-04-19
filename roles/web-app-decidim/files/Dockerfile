ARG DECIDIM_IMAGE
ARG DECIDIM_VERSION
FROM ${DECIDIM_IMAGE}:${DECIDIM_VERSION}

# Set SSL cert for Ruby OpenSSL to trust local CA
# SSL cert will be set at runtime via CURL_CA_BUNDLE

# Add omniauth_openid_connect to Gemfile and install
RUN echo "gem 'omniauth_openid_connect'" >> /code/Gemfile && \
    cd /code && bundle install --quiet

# Patch secrets.yml and omniauth initializer
RUN python3 - << 'PYEOF'
import re

# 1. Patch secrets.yml — add openid_connect to default and development omniauth sections
secrets_path = "/code/config/secrets.yml"
with open(secrets_path, "r") as f:
    content = f.read()

oidc_block = """    openid_connect:
      enabled: <%= Decidim::Env.new("OIDC_ENABLED").to_boolean_string %>
      icon: login-box-line
      client_id: <%= ENV["OIDC_CLIENT_ID"] %>
      client_secret: <%= ENV["OIDC_CLIENT_SECRET"] %>
      site: <%= ENV["OIDC_ISSUER"] %>
      issuer: <%= ENV["OIDC_ISSUER"] %>
      discovery: true
      scope: ["openid", "email", "profile"]
"""

content = content.replace(
    '      client_secret: <%= ENV["OMNIAUTH_GOOGLE_CLIENT_SECRET"] %>',
    '      client_secret: <%= ENV["OMNIAUTH_GOOGLE_CLIENT_SECRET"] %>\n' + oidc_block.rstrip()
)
content = content.replace(
    '    developer:\n      enabled: true\n      icon: phone-line',
    '    developer:\n      enabled: true\n      icon: phone-line\n' + oidc_block.rstrip()
)
with open(secrets_path, "w") as f:
    f.write(content)
print("secrets.yml patched")

# 2. Patch omniauth.rb — add openid_connect provider registration
omniauth_path = "/usr/local/bundle/gems/decidim-core-0.28.0/config/initializers/omniauth.rb"
with open(omniauth_path, "r") as f:
    content = f.read()
injection = """
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
content = re.sub(r'(  end\nend\s*)$', injection + r'\1', content.rstrip()) + '\n'
with open(omniauth_path, "w") as f:
    f.write(content)
print("omniauth.rb patched")

# 3. Patch omniauth_helper.rb — return correct icon for openid_connect
helper_path = "/usr/local/bundle/gems/decidim-core-0.28.0/app/helpers/decidim/omniauth_helper.rb"
with open(helper_path, "r") as f:
    content = f.read()
content = content.replace(
    "    def oauth_icon(provider)",
    '    def oauth_icon(provider)\n      return icon("login-box-line") if provider.to_sym == :openid_connect'
)
with open(helper_path, "w") as f:
    f.write(content)
print("omniauth_helper.rb patched")
PYEOF
