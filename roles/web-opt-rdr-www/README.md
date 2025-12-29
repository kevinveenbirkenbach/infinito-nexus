# Nginx WWW Redirect 🌐

## Description
Automates the creation of Nginx server blocks that redirect all `www.` subdomains to their non-www equivalents. Simple, idempotent, and SEO-friendly! 🚀

## Overview
This role will:
- **Discover** existing `*.conf` vhosts in your Nginx servers directory  
- **Filter** domains with or without your `DOMAIN_PRIMARY`  
- **Generate** redirect rules via the `web-opt-rdr-domains` role  
- **Optionally** include a wildcard redirect template (experimental) ⭐️  
- **Clean up** leftover configs when running in cleanup mode 🧹  

All tasks are guarded by “run once” facts and `MODE_CLEANUP` flags to avoid unintended re-runs or stale files.

## Purpose
Ensure that any request to `www.example.com` automatically and permanently redirects to `https://example.com`, improving user experience, SEO, and certificate management. 🎯

## Features
- **Auto-Discovery**: Scans your Nginx `servers` directory for `.conf` files. 🔍  
- **Dynamic Redirects**: Builds `source: "www.domain"` → `target: "domain"` mappings on the fly. 🔧  
- **Wildcard Redirect**: Includes a templated wildcard server block for `www.*` domains (toggleable). ✨  
- **Cleanup Mode**: Removes the wildcard config file when `CERTBOT_FLAVOR` is set to `dedicated` and `MODE_CLEANUP` is enabled. 🗑️
- **Debug Output**: Optional `MODE_DEBUG` gives detailed variable dumps for troubleshooting. 🐛  
