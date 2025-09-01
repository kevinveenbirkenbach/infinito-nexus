# Nginx Matomo Tracking Role

This Ansible role automates the integration of Matomo tracking code into Nginx-served websites. It simplifies the process of adding the Matomo analytics tracking script and image tracker to all your web pages served through Nginx.

## Features
- Automated insertion of Matomo tracking script into the `</head>` tag of HTML pages.
- Integration of a noscript image tracker before the `</body>` tag for tracking users with JavaScript disabled.
- Configuration to apply changes on every request, ensuring that dynamic content and single-page applications are also tracked.

## Requirements
- Nginx installed on the target server.
- Matomo analytics platform set up and accessible.

## Dependencies
- None. This role is designed to be included in Nginx server block configurations.

## Customization
You can customize the tracking script and the noscript image tracker by editing the `matomo-tracking.js.j2` and `matomo.subfilter.conf.j2` templates.

## Author Information
This role was created in 2023 by [Kevin Veen Birkenbach](https://www.veen.world/), providing a seamless way to add Matomo analytics to any website served via Nginx.