# Zoom

## Overview
Welcome to the `desk-zoom` role documentation, a part of the `infinito` repository. This role is focused on installing video conferencing software on Linux systems, specifically tailored for personal use and remote work requirements.

## Role Tasks
The `main.yml` file in the `desk-zoom` role includes tasks for setting up video conferencing tools:

1. **Install Video Conference Software**:
   - Utilizes the `kewlfft.aur.aur` module with `yay` as the helper to install `zoom`, a popular video conferencing application.

## Other Resources
- As noted, the Microsoft Teams client is no longer natively supported on Linux. For more information and potential workarounds, you can visit the [AUR package page for Teams](https://aur.archlinux.org/packages/teams).

## Dependencies
This role relies on:
- **sys-aur**: Ensures that an Arch User Repository (AUR) helper is installed, necessary for installing software like Zoom which may not be available in standard repositories.

## Purpose and Usage
The `desk-zoom` role is particularly useful for professionals, educators, and anyone who needs reliable video conferencing capabilities on their Linux system. With the increasing demand for remote communication, this role provides an efficient way to set up key video conferencing tools.

## Prerequisites
- **Ansible**: Required to run this role.
- **Arch Linux-based System**: Given the use of `yay` and AUR, this role is designed for Arch Linux or similar distributions.

## Running the Role
To utilize this role:
1. Clone the `infinito` repository.
2. Navigate to the `roles/desk-zoom` directory.
3. Run the role using Ansible, ensuring you have appropriate system permissions for software installation.

## Customization
You can customize this role by adding or modifying the video conferencing tools installed. For example, if there's a need for other applications like Skype or Google Meet, these can be included in the task list.

## Support and Contributions
For support, feedback, or contributions, such as adding support for additional video conferencing tools or improving existing configurations, please open an issue or submit a pull request in the `infinito` repository. Contributions that enhance the role's functionality are highly welcome.