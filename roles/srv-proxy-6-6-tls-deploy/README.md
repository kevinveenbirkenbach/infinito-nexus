# Nginx Docker Cert Deploy Role

🎉 **Author**: [Kevin Veen-Birkenbach](https://www.veen.world)

This Ansible role simplifies the deployment of **Let's Encrypt certificates** into **Docker Compose** setups with Nginx. It supports both **individual certificates per subdomain** and a **single wildcard certificate** for all subdomains.

---

## 🚀 **Features**
- Automatically deploys **Let's Encrypt certificates** to Docker Compose setups.
- Supports both **single-domain certificates** and **one wildcard certificate** for all subdomains.
- **Copies certificates** to the target directory inside the container.
- Automatically **reloads or restarts Nginx services** when certificates are updated.
- **Configures and manages a `systemd` service** for automated certificate deployment.
- **Includes a `systemd` timer** for scheduled renewals.
- **Handles dependent services** like `sys-alm-compose`.

---

## 🔧 **Tasks Overview**

### **1️⃣ Main Tasks**
1. **Add Deployment Script**  
   - Copies `srv-proxy-6-6-tls-deploy.sh` to the administrator scripts directory.
   
2. **Create Certificate Directory**  
   - Ensures `cert_mount_directory` exists with proper permissions.
   
3. **Configure `systemd` Service**  
   - Deploys a `systemd` service file for the deployment process.
   
4. **Include `sys-timer` Role**  
   - Schedules automatic certificate deployment using a `systemd` timer.

### **2️⃣ Handlers**
- **Restart Nginx Service**  
  - Restarts `srv-proxy-6-6-tls-deploy` whenever a certificate update occurs.

---

## **🔧 Deploying Certificates into Docker Containers**
The role **automates copying certificates** into Docker Compose setups.

### **1️⃣ Deployment Script (`srv-proxy-6-6-tls-deploy.sh`)**
This script:
- **Copies certificates** to the correct container directory.
- **Reloads Nginx** inside all running containers.
- **Restarts containers if needed**.

**Usage:**
```sh
sh srv-proxy-6-6-tls-deploy.sh PRIMARY_DOMAIN /path/to/docker/compose
```

---

## 🎯 **Summary**
| Feature | Description |
|---------|------------|
| **Single-domain & wildcard support** | Use individual certs or a wildcard certificate |
| **Automated renewal** | Cronjob or systemd timer ensures auto-renewals |
| **Docker-ready** | Deploys certificates directly into Docker containers |
| **Supports Nginx & Mailu** | Compatible with multiple services |
| **Systemd integration** | Automates deployment via `systemd` |

🚀 **Now your Nginx setup is fully automated and secured with Let's Encrypt!** 🎉
```