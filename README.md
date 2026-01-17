# Infinito.Nexus 🚀

**🔐 One login. ♾️ Infinite application** 

![Infinito.Nexus Logo](assets/img/logo.png)
---

## What is Infinito.Nexus? 📌

**Infinito.Nexus** is an **automated, modular infrastructure framework** built on **Docker**, **Linux**, and **Ansible**, equally suited for cloud services, local server management, and desktop workstations. At its core lies a **web-based desktop with single sign-on**—backed by an **LDAP directory** and **OIDC**—granting **seamless access** to an almost limitless portfolio of self-hosted applications. It fully supports **ActivityPub applications** and is **Fediverse-compatible**, while integrated **monitoring**, **alerting**, **cleanup**, **self-healing**, **automated updates**, and **backup solutions** provide everything an organization needs to run at scale.

| 📚 | 🔗 |
|---|---|
| 🌐 Try It Live | [![Infinito.Nexus](https://img.shields.io/badge/Infinito.Nexus-%2ECloud-000000?labelColor=004B8D&style=flat&borderRadius=8)](https://infinito.nexus) |
| 🔧 Request Your Setup       | [![CyberMaster.Space](https://img.shields.io/badge/CyberMaster-%2ESpace-000000?labelColor=004B8D&style=flat&borderRadius=8)](https://cybermaster.space) |
| 📖 About This Project  | [![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-blue?logo=github)](https://github.com/sponsors/kevinveenbirkenbach) [![View Source](https://img.shields.io/badge/View_Source-Repository-000000?logo=github&labelColor=004B8D&style=flat&borderRadius=8)](https://s.infinito.nexus/code) |
| ☕️ Support Us               |  [![Patreon](https://img.shields.io/badge/Support-Patreon-orange?logo=patreon)](https://www.patreon.com/c/kevinveenbirkenbach) [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20Coffee-Funding-yellow?logo=buymeacoffee)](https://buymeacoffee.com/kevinveenbirkenbach) [![PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://s.veen.world/paypaldonate) [![Sponsor Infinito.Nexus](https://img.shields.io/badge/Donate–Infinito.Nexus-000000?style=flat&labelColor=004B8D&logo=github-sponsors&logoColor=white&borderRadius=8)](https://github.com/sponsors/kevinveenbirkenbach) |

---

## Key Features 🎯

* **Automated Deployment** 📦
  Turn up servers and workstations in minutes with ready-made Ansible roles.

* **Enterprise-Grade Security** 🔒
  Centralized user management via LDAP & OIDC (Keycloak), plus optional 2FA and encrypted storage.

* **Modular Scalability** 📈
  Grow from small teams to global enterprises by composing only the services you need.

* **Fediverse & ActivityPub Support** 🌐
  Seamlessly integrate Mastodon, Peertube, Matrix and other ActivityPub apps out of the box.

* **Self-Healing & Maintenance** ⚙️
  Automated cleanup, container healing, and auto-updates keep infrastructure healthy without human intervention.

* **Monitoring, Alerting & Analytics** 📊
  Built-in system, application, and security monitoring with multi-channel notifications.

* **Backup & Disaster Recovery** 💾
  Scheduled backups and scripted recovery processes to safeguard your data.

* **Continuous Updates** 🔄
  Automatic patching and version upgrades across the stack.

* **Application Ecosystem** 🚀
  A curated suite of self-hosted apps—from **project management**, **version control**, and **CI/CD** to **chat**, **video conferencing**, **CMS**, **e-learning**, **social networking**, and **e-commerce**—all seamlessly integrated.

More informations about the features you will find [here](docs/overview/Features.md).

---

## Get Started 🚀

### Use it online 🌐 

Try [Infinito.Nexus](https://infinito.nexus) – sign up in seconds, explore the platform, and discover what our solution can do for you! 🚀🔧✨

### Install locally 💻
1. **Install Infinito.Nexus** via [Kevin's Package Manager](https://github.com/kevinveenbirkenbach/package-manager)
2. **Setup Infinito.Nexus** using:
   ```sh
   pkgmgr install infinito
   ```
3. **Explore Commands** with:
   ```sh
   infinito --help
   ```
---

### Setup with Docker🚢

Get Infinito.Nexus up and running inside Docker in just a few steps. For detailed build options and troubleshooting, see the [Docker Guide](docs/Docker.md).

```bash
# 1. Build the Docker image: the Docker image:
docker build -t infinito:latest .

# 2. Run the CLI interactively:
docker run --rm -it infinito:latest infinito --help
```

---

## License ⚖️

Infinito.Nexus is distributed under the **Infinito.Nexus NonCommercial License**. Please see [LICENSE.md](LICENSE.md) for full terms.

---

## Professional Setup & Support 💼

For expert installation and configuration visit [cybermaster.space](https://cybermaster.space/) or write to us at **[contact@cymais.cloud](mailto:contact@cymais.cloud)**.
