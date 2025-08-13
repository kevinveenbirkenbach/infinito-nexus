# Debug Variables Task Include

This task file (`tasks/utils/debug/main.yml`) outputs key variables for troubleshooting Ansible roles and playbooks.

## Purpose

Use this file to quickly debug and inspect variables such as `application_id`, `applications`, `ports`, and more. It helps identify missing or misconfigured variables during playbook runs.

## Usage

Include the debug file in any task list or role:

```yaml
- import_tasks: utils/debug/main.yml
````

or

```yaml
- include_tasks: utils/debug/main.yml
```

Optionally, enable it conditionally:

```yaml
- import_tasks: utils/debug/main.yml
  when: MODE_DEBUG | default(false)
```

**Note:**
The path is relative to the directory of your task file.

---

This tool is intended for development and troubleshooting only. Remove or disable it in production runs.