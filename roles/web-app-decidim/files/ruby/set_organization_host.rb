org = Decidim::Organization.first
org.host = ENV.fetch("DECIDIM_ORG_HOST")
org.save
puts "Organization host set to: #{org.host}"
