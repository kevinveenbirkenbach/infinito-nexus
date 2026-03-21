# Shared Utility Code (`module_utils/`) for Infinito.Nexus

This directory contains shared Python utility code (also known as "library code") for use by custom Ansible modules, plugins, or roles in the Infinito.Nexus project.

## When to Use `module_utils`

- **Shared logic:** Use `module_utils` to define functions, classes, or helpers that are shared across multiple custom modules, plugins, or filter/lookups in your project.
- **Reduce duplication:** Centralize code such as API clients, input validation, complex calculations, or protocol helpers.
- **Maintainability:** If you find yourself repeating code in different custom modules/plugins, refactor it into `module_utils/`.

### Examples

- Shared HTTP(S) connection handler for multiple modules.
- Common validation or transformation functions for user input.
- Utility functions for interacting with Docker, LDAP, etc.
- Grouped helper packages such as `module_utils/domains/` for related domain logic.

## Usage Example

In a custom Ansible module or plugin:
```python
from module_utils.domains.primary_domain import get_primary_domain
````

## When *not* to Use `module_utils`

* Do not place standalone Ansible modules or plugins here—those go into `library/`, `filter_plugins/`, or `lookup_plugins/` respectively.
* Only use for code that will be **imported** by other plugins or modules.

## Further Reading

* [Ansible Module Utilities Documentation](https://docs.ansible.com/ansible/latest/dev_guide/developing_module_utilities.html)
* [Best Practices: Reusing Code with module\_utils](https://docs.ansible.com/ansible/latest/dev_guide/developing_plugins.html#sharing-code-among-plugins)
