# 🌐 Global JavaScript Injector for NGINX

## Description

This Ansible role injects a custom JavaScript snippet into all HTML responses served by NGINX. It leverages NGINX’s `sub_filter` to seamlessly insert your application-specific script just before the closing `</head>` tag, ensuring that your code runs on every page load—perfect for global feature flags, analytics, or UI enhancements.

## Features

- **One-line Script Injection**  
  Collapses your JavaScript into a single line and injects it via `sub_filter` for minimal footprint and maximal compatibility.

- **Easy CSP Integration**  
  Automatically computes and appends a CSP hash entry for your script, so you can lock down Content Security Policy without lifting a finger.

- **Conditional Activation**  
  Activates only when you enable the `javascript` feature for a given application, keeping your server blocks clean and performant.

- **Debug Mode**  
  Supports an `MODE_DEBUG` flag that appends optional `console.log` statements for easier troubleshooting in staging or development.

## Author

Developed by **Kevin Veen-Birkenbach**
Consulting & Coaching Solutions — [veen.world](https://www.veen.world)

---

Happy automating! 🎉
