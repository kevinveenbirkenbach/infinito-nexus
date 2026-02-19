# sys-package

## Description

This role installs additional system packages defined directly in host or group inventory variables.

## Variables

- `SYS_PACKAGES` (list, default: `[]`)
  List of package names to install with the system package manager.

## Inventory Example

```yaml
all:
  hosts:
    myhost:
      SYS_PACKAGES:
      - htop
      - tree
      - jq
```

When `SYS_PACKAGES` is empty, the role does nothing.
