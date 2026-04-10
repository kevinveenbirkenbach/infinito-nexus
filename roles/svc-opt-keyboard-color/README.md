# MSI Keyboard Driver
Ansible role to set up dynamic keyboard color change on MSI laptops.
## Requirements
- An MSI laptop
- The `msi-perkeyrgb` tool installed on the system
- Ansible 2.9 or later
## Role Variables
Available variables are listed below, along with their default values:
```yaml
vendor_and_product_id: ""
```
The `vendor_and_product_id` variable is required and should be set to the vendor and product ID of the MSI laptop.
## Author
This role was created by [Kevin Veen-Birkenbach](https://github.com/kevinveenbirkenbach).
