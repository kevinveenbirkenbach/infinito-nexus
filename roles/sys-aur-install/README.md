# sys-aur-install

Installs one or more AUR packages using `kewlfft.aur.aur` and the `yay` helper.

## Variables

- `yay_install_packages` (required for direct role usage): list of AUR package names
- `yay_install_use` (optional): helper binary, default `yay`
- `yay_install_become_user` (optional): user to execute AUR install, default `aur_builder`
- `SYS_AUR_PACKAGES` (inventory default): list used by constructor auto-install flow

## Example

```yaml
- name: Install MSI packages
  include_role:
    name: sys-aur-install
  vars:
    yay_install_packages:
      - msi-perkeyrgb
```
