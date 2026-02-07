# NGINX File Server

## 🔥 Description

The NGINX File Server role sets up a simple and secure static file server using [NGINX](https://NGINX.org/). It provides an easy way to serve files over HTTPS, including directory listing, `.well-known` support, and automatic SSL/TLS certificate integration via Let's Encrypt.

## 📖 Overview

Optimized for Archlinux, this role configures NGINX to act as a lightweight and efficient file server. It ensures that files are served securely, with optional directory browsing enabled, and proper MIME type handling for standard web clients.

### Key Features
- **HTTPS Secured File Hosting:** Automatically retrieves SSL/TLS certificates using Let's Encrypt.
- **Autoindex Directory Listing:** Displays files and folders in a clean and human-readable format.
- **.well-known Support:** Fully supports ACME and other `.well-known` path requirements.
- **Customizable File Path:** Easily adjust the root directory for your files through Ansible variables.
- **Local Time Display:** Enhances directory listings by showing local timestamps.

## 🎯 Purpose

The NGINX File Server role is ideal for hosting static files, sharing resources internally or externally, and serving ACME challenges for certificate issuance. It offers a reliable and minimalistic alternative to more complex file-sharing solutions.

## 🚀 Features

- **Automatic SSL/TLS Certificate Management:** Integrates with Let's Encrypt for secure access.
- **Simple Configuration:** Minimal setup with clear, maintainable templates.
- **Directory Listings:** Enables browsing through served files with human-readable file sizes and timestamps.
- **Static Content Hosting:** Serve any type of static files (documents, software, media, etc.).
- **Well-Known Folder Support:** Allows serving validation files and other standardized resources easily.

## 🔗 Learn More

- [NGINX Official Website](https://NGINX.org/)
- [Let's Encrypt](https://letsencrypt.org/)
- [HTTP File Server (Wikipedia)](https://en.wikipedia.org/wiki/HTTP_file-server)
- [HTTPS (Wikipedia)](https://en.wikipedia.org/wiki/HTTPS)
