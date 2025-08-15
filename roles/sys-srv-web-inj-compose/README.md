# Nginx Global Matomo & Theming Modifier Role 🚀

This role enhances your Nginx configuration by conditionally injecting global Matomo tracking and theming elements into your HTML responses. It uses Nginx sub-filters to seamlessly add tracking scripts and CSS links to your web pages.

---

## Features

- **Global Matomo Tracking**  
  The role includes Matomo tracking configuration and injects the corresponding tracking script into your HTML.

- **Global Theming**  
  The role injects a global CSS link for consistent theming across your site.

- **Smart Injection**  
  Uses Nginx's `sub_filter` to insert the tracking and theming snippets right before the closing `</head>` tag of your HTML documents.


This will automatically activate Matomo tracking and/or global theming based on your configuration.

---

## Author

Developed by [Kevin Veen-Birkenbach](https://www.veen.world) 😎

---

Happy automating! 🎉