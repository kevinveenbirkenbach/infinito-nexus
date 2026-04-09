# Role README

Every Ansible role MUST contain a `README.md` at the role root.
This page defines the required structure and content rules.

## Structure

Role README files MUST follow this section order.
Optional sections MAY be omitted when they add no value for the role.

### 1. Title (required)

The H1 heading MUST be the human-readable name of the application or service, not the role ID.

```markdown
# Nextcloud
```

### 2. Description (required)

A short paragraph that describes what the **software** is — not what the role does.
Link the software name to its official website on first use.

```markdown
## Description

[Nextcloud](https://nextcloud.com/) is a self-hosted file sync and share platform …
```

### 3. Overview (required)

A short paragraph that describes what the **role** does — what it deploys, configures, and integrates.
Reference any companion documentation files (e.g. `Administration.md`) here using file-name link text.

```markdown
## Overview

This role deploys Nextcloud using Docker Compose …
For administration details see [Administration.md](./Administration.md).
```

### 4. Features (required)

A bulleted list of the most important capabilities.
Each item MUST start with a **bold** label followed by a colon and a short explanation.

```markdown
## Features

- **Self-hosted:** Run the application under your own domain …
- **LDAP Integration:** Authenticate users via a central directory …
```

### 5. Purpose (optional)

Use this section when the motivation for the role is not obvious from Description and Overview.
Omit it for roles where the purpose is self-evident.

### 6. Developer Notes (optional)

Link to role-local documentation files such as `Administration.md`, `Installation.md`, or `Development.md`.
Use file-name link text, never the full path.

```markdown
## Developer Notes

See [Administration.md](./Administration.md) for live container inspection and LDAP configuration.
```

### 7. Further Resources (optional)

A list of external links relevant to the software or the deployment.
Link text MUST be a descriptive label or the domain name — never the full URL.

```markdown
## Further Resources

- [Nextcloud Official Website](https://nextcloud.com/)
- [Nextcloud Admin Manual](https://docs.nextcloud.com/…)
```

### 8. Credits (required)

Always the last section. MUST follow this fixed format:

```markdown
## Credits

Developed and maintained by **Kevin Veen-Birkenbach**.
Learn more at [veen.world](https://www.veen.world).
Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code).
Licensed under the [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license).
```

## Formatting Rules

- Role README files MUST NOT use emojis in headings.
  Emojis in role READMEs interfere with automated tooling that parses heading text.
- Body text MAY use emojis where they improve readability.
- All headings MUST use sentence-case (capitalize only the first word and proper nouns).
- Link text MUST follow the rules in [documentation.md](../../documentation.md).
