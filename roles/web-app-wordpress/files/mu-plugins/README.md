# WordPress Must-Use Plugins 🔒

## Scope 🎯

This directory holds PHP files that the [web-app-wordpress](../../) role copies into the running container at `/var/www/html/wp-content/mu-plugins/`.

`mu-plugins` is a WordPress core convention for **must-use plugins**. WordPress automatically loads every top-level `*.php` file in that directory before normal plugins, without a database activation record. As a result, code shipped here:

- MUST be loaded on every request as soon as the file is present.
- MUST NOT be deactivated from the `Plugins -> Must-Use` admin screen.
- MUST NOT be placed in a subdirectory, because WordPress does not recurse into `mu-plugins`.

See the [WordPress Must-Use Plugins handbook](https://developer.wordpress.org/advanced-administration/plugins/mu-plugins/) for the upstream contract.

## When to add code here 📋

Put a file in this directory only when the behavior it implements is part of the security or integration contract of this role and MUST remain in effect for every request. Everyday feature plugins SHOULD stay in normal `wp-content/plugins/` and be managed through [03_enable_plugin.yml](../../tasks/03_enable_plugin.yml) so operators can disable them per site if needed.

Each file in this directory SHOULD declare its purpose, hooks, and source requirement at the top of the file so readers can understand why it cannot be switched off.

## Deployment 🚚

Files in this directory are copied into the running container by [05_mu_plugins.yml](../../tasks/05_mu_plugins.yml). The task runs on every deploy, so dropping a new file here is enough to have it picked up on the next playbook run.

## Credits 🙏

Developed and maintained by **Kevin Veen-Birkenbach**.
Learn more at [veen.world](https://www.veen.world).
Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code).
Licensed under the [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license).
