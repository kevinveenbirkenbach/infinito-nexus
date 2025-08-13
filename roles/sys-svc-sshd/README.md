# sshd

## Description

This Ansible role configures the OpenSSH daemon (`sshd`) by deploying a templated `sshd_config` file. It applies secure, best-practice settings—such as disabling root login, enforcing public-key authentication, and setting appropriate logging levels—to harden remote access and reduce the risk of misconfiguration or lockout.

## Overview

- Renders `sshd_config.j2` into `/etc/ssh/sshd_config` with customizable options  
- Sets file ownership (`root:root`) and permissions (`0644`)  
- Automatically reloads and restarts the SSH service via a Systemd handler  
- Uses a `run_once_sys_svc_sshd` fact to ensure idempotent execution  

## Features

- **Templated Configuration**  
  Delivers a Jinja2-based `sshd_config` with variables for debug logging and PAM support.

- **Security Defaults**  
  - Disables password (`PasswordAuthentication no`) and root login (`PermitRootLogin no`)  
  - Enforces public-key authentication (`PubkeyAuthentication yes`)  
  - Conditionally sets `LogLevel` to `DEBUG3` when `MODE_DEBUG` is true  

- **Systemd Integration**  
  Handles daemon reload and service restart seamlessly on configuration changes.

- **Idempotency**  
  Ensures tasks run only once per play by setting the `run_once_sys_svc_sshd` fact.

## Further Resources

- [sshd_config Manual (OpenSSH)](https://man7.org/linux/man-pages/man5/sshd_config.5.html)  
- [Ansible Template Module](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/template_module.html)  
- [Ansible Shell & Handler Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_handlers.html)  
- [OpenSSH Security Recommendations](https://www.openssh.com/security.html)  
