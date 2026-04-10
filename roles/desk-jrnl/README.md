# Jrnl Role for Ansible
## Overview
This role automates the installation of Jrnl, a simple and effective command-line journal application. It uses the `community.general.pacman` module for systems that support the Pacman package manager, ensuring that Jrnl is installed and up to date.
## Requirements
- Ansible 2.9 or higher.
- Access to Pacman package manager (commonly available on Arch Linux and derivatives).
## Role Variables
No additional role variables are needed for this role as it solely focuses on the installation of Jrnl.
## Dependencies
No external dependencies.
## Example Playbook
Including this role in your playbook is straightforward. Simply add the role to your playbook's roles section:
```yaml
- hosts: all
  roles:
    - desk-jrnl
```
## Further Resources
For more detailed information on Jrnl and its functionalities, visit [Jrnl's official documentation](https://jrnl.sh/).
## Contributing
Contributions to this role are welcome. Please adhere to standard coding conventions and best practices.
## Other Resources
This role was created as part of a larger playbook.