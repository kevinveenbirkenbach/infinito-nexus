org = Decidim::Organization.first
settings = org.omniauth_settings || {}
settings["omniauth_settings_openid_connect_enabled"] = true
org.omniauth_settings = settings
org.save!
puts "OIDC settings configured"
