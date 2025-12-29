## **🔐 Wildcard Certificate Setup with Let's Encrypt**
If you enabled `enable_wildcard_certificate`, follow these steps to manually request a **wildcard certificate**.

### **1️⃣ Run the Certbot Command 🖥️**
```sh
certbot certonly --manual --preferred-challenges=dns --agree-tos \
--email administrator@DOMAIN_PRIMARY -d DOMAIN_PRIMARY -d "*.DOMAIN_PRIMARY"
```

### **2️⃣ Add DNS TXT Record for Validation 📜**
Certbot will prompt you to add a DNS TXT record:
```
Please create a TXT record under the name:
_acme-challenge.DOMAIN_PRIMARY.

with the following value:
9oVizYIYVGlZ3VtWQIKRS5UghyXiqGoUNlCtIE7LiA
```
➡ **Go to your DNS provider** and create a new **TXT record**:  
   - **Host:** `_acme-challenge.DOMAIN_PRIMARY`  
   - **Value:** `"9oVizYIYVGlZ3VtWQIKRS5UghyXiqGoUNlCtIE7LiA"`  
   - **TTL:** Set to **300 seconds (or lowest possible)**  

✅ **Verify the DNS record** before continuing:  
```sh
dig TXT _acme-challenge.DOMAIN_PRIMARY @8.8.8.8
```

### **3️⃣ Complete the Certificate Request ✅**
Once the DNS changes have propagated, **press Enter** in the Certbot terminal.  
If successful, Certbot will save the certificates under:  
```
/etc/letsencrypt/live/DOMAIN_PRIMARY/
```
- **fullchain.pem** → The certificate  
- **privkey.pem** → The private key  
