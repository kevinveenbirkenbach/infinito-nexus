## Add LDAP Users Manually for Immediate Sharing

In a default Nextcloud + LDAP setup, user accounts are only created in the internal Nextcloud database **after their first login**. This means that even if a user exists in LDAP, they **cannot receive shared files or folders** until they have logged in at least once—or are manually synchronized.

To make LDAP users available for sharing **without requiring initial login**, follow these steps:

### 1. Search for the User in LDAP

Check if the user exists in the configured LDAP directory:

```bash
docker exec -u www-data nextcloud php occ ldap:search <username>
```

If the user is found, proceed to the next step.

### 2. Create the User in Nextcloud from LDAP

Manually trigger a sync to register the user in the Nextcloud database:

```bash
docker exec -u www-data nextcloud php occ ldap:check-user --update <username>
```

**Example:**

```bash
docker exec -u www-data nextcloud php occ ldap:check-user --update viktoriakaffanke
```

Once executed, the user becomes fully available in the system—for sharing, group membership, and permissions—even without logging in.

### 3. Synchronize All Known Users (Optional)

To synchronize account data (display name, mail address, group memberships, etc.) for **all users** currently known to Nextcloud:

```bash
docker exec -u www-data nextcloud php occ user:sync-account-data
```

This step is especially useful after modifying LDAP attributes or group memberships, ensuring up-to-date data in the Nextcloud UI and permission system.