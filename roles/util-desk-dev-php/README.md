# PHP Development Utilities 🐘

## Description

This Ansible role provides a minimal setup for PHP development on Arch Linux. It installs the PHP interpreter and establishes the foundation for web and backend development using PHP.

Explore more at the [PHP Official Site](https://www.php.net/), [Arch Wiki - PHP](https://wiki.archlinux.org/title/PHP), and [Wikipedia – PHP](https://en.wikipedia.org/wiki/PHP).

## Overview

The `util-desk-dev-php` role extends the base developer persona by adding support for PHP development. It's ideal for backend developers, web engineers, and students working with PHP-based applications and frameworks.

## Purpose

To equip developer environments with PHP so that users can begin writing and running PHP scripts or building full-stack applications with common PHP frameworks like Laravel or Symfony.

## Features

- **Installs PHP:** Adds the official PHP interpreter from the Arch package repositories.
- **Lightweight & Extensible:** Can be extended with PHP modules, web servers, or frameworks.
- **Persona Integration:** Builds on the `util-desk-dev-core` role for consistent tooling and workflow.

## Customization

This role can be extended with:
- PHP extensions (`php-gd`, `php-pgsql`, etc.)
- Composer (`composer`)
- Web servers like Apache or NGINX
- Frameworks like Laravel or Symfony

Let the role grow as your stack does.

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus NonCommercial License (CNCL)](https://s.infinito.nexus/license)