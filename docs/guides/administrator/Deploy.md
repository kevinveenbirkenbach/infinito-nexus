# 🚀 Deployment Guide

This section explains how to deploy and manage **[Infinito.Nexus](https://infinito.nexus)** using Ansible. Infinito.Nexus uses a collection of Ansible tasks, which are controlled via different **"modes"** — such as **updates**, **backups**, **resets**, and **cleanup** operations.

---

## ✅ Prerequisites

Before deploying, ensure the following are in place:

- **🧭 Inventory File:** A valid Ansible inventory file that defines your target systems (servers, personal computers, etc.). Adjust example paths to your environment.
- **📦 Infinito.Nexus Installed:** Install via [Kevin's Package-Manager](https://github.com/kevinveenbirkenbach/package-manager).
- **🔐 (Optional) Vault Password File:** If you don't want to enter your vault password interactively, create a password file.

---

## 📘 Show Infinito.Nexus Help

To get a full overview of available options and usage instructions, run:

```bash
infinito --help
```

---

## 💡 Example Deploy Command

To deploy Infinito.Nexus on a personal computer (e.g., a laptop), you can run:

```bash
infinito playbook \
  --limit hp-spectre-x360 \
  --host-type personal-computer \
  --update \
  --password-file ~/Repositories/git.veen.world/kevinveenbirkenbach/computer-inventory/.pass/general.txt \
  ~/Repositories/git.veen.world/kevinveenbirkenbach/computer-inventory/pcs.yml
```

### 🧠 What does this command do?

| Parameter | Description |
|----------|-------------|
| `playbook` | Executes the playbook subcommand of Infinito.Nexus. |
| `--limit hp-spectre-x360` | Limits execution to a specific host (`hp-spectre-x360`). |
| `--host-type personal-computer` | Defines the host type. Default is `server`; here it is set to `personal-computer`. |
| `--update` | Enables update mode to apply software or configuration updates. |
| `--password-file` | Specifies the vault password file path for decrypting sensitive values. |
| `pcs.yml` | The path to the inventory file containing host definitions. |

---

## 🔐 Using a Vault Password File

To avoid typing your vault password interactively, you can provide a file:

```bash
--password-file /path/to/your/vault_pass.txt
```

> ⚠️ **Security Tip:** Ensure the password file is properly protected (e.g., `chmod 600 vault_pass.txt`).

---

## 🔍 Full Command-Line Reference

Here’s a breakdown of all available parameters from `infinito playbook --help`:

| Argument | Description |
|----------|-------------|
| `inventory` *(positional)* | Path to the Ansible inventory file. |
| `--limit <HOST>` | Run the playbook only on the specified host. |
| `--host-type {server, personal-computer}` | Define the target system type (default is `server`). |
| `--reset` | Enables reset mode (restores or resets specific configurations). |
| `--test` | Enables test mode (dry-run style). No actual changes are applied. |
| `--update` | Enables update mode to upgrade packages or configs. |
| `--backup` | Triggers backup routines for data or configurations. |
| `--cleanup` | Cleans up temporary files, old data, etc. |
| `--debug` | Enables debug logging in the playbook. |
| `--password-file <PATH>` | Uses a vault password file instead of interactive prompt. |
| `-v, -vv, -vvv` | Increases output verbosity. More `v`s = more detail. |

---

## 🔧 Combine Multiple Modes

You can mix and match modes like this:

```bash
infinito playbook --update --backup --cleanup pcs.yml
```

This will update the system, create a backup, and clean up unnecessary files in one run.

---

## 📝 Footnote

> 📄 *This documentation page was generated with the help of AI.*  
> 🤖 [View the original conversation (ChatGPT)](https://chatgpt.com/share/67ecfe25-3fb8-800f-923d-8cd3fc4efd2f)