    if ENV["OIDC_ENABLED"].to_s == "true"
      require "omniauth_openid_connect"
      ENV["SSL_CERT_FILE"] = ENV["CURL_CA_BUNDLE"] if ENV["CURL_CA_BUNDLE"] && File.exist?(ENV["CURL_CA_BUNDLE"].to_s)
      provider(
        :openid_connect,
        name: :openid_connect,
        scope: [:openid, :email, :profile],
        response_type: :code,
        discovery: true,
        issuer: ENV.fetch("OIDC_ISSUER"),
        client_options: {
          host: URI.parse(ENV.fetch("OIDC_ISSUER")).host,
          identifier: ENV.fetch("OIDC_CLIENT_ID"),
          secret:     ENV.fetch("OIDC_CLIENT_SECRET"),
          redirect_uri: "#{ENV.fetch('APPLICATION_HOST').chomp('/')}/users/auth/openid_connect/callback"
        }
      )
    end
