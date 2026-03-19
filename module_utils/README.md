# Shared Utilities (`module_utils/`)

This directory contains shared Python helpers used by custom modules and plugins.

## Purpose

Use `module_utils/` for reusable code that should not be duplicated across:
- `library/` modules,
- `plugins/action/`,
- `plugins/filter/`,
- `plugins/lookup/`.

Typical shared utilities:
- API clients,
- validation/conversion helpers,
- path and configuration helpers,
- cross-plugin/module domain logic.

## Design Guidelines

- Keep helpers focused and composable.
- Avoid side effects during import.
- Prefer explicit function/class APIs over implicit globals.
- Keep dependencies minimal so modules/plugins stay lightweight.

## Example Import

```python
from module_utils.my_shared_utils import some_helper
```

## What Does Not Belong Here

- Standalone executable modules (put in `library/`).
- Ansible plugin entrypoints (put in `plugins/*`).

## References

- Module utilities: <https://docs.ansible.com/ansible/latest/dev_guide/developing_module_utilities.html>
- Plugin development: <https://docs.ansible.com/ansible/latest/dev_guide/developing_plugins.html>
