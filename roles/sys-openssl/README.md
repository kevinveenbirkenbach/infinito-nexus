# sys-openssl

Ensures that the `openssl` CLI is installed on the host.

This role is intended as a shared dependency for other roles that execute
OpenSSL commands on the host system.

## Behavior

- Installs package: `openssl`
- Uses standard Infinito run-once flagging via `run_once_sys_openssl`

## Usage

```yaml
- include_role:
    name: sys-openssl
  when: run_once_sys_openssl is not defined
```
