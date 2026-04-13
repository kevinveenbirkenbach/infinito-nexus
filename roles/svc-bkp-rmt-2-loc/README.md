# Backup Remote to Local

## Description

This role pulls backups from a remote server and stores them locally using rsync with retry logic. It retrieves remote backup data and integrates with your overall backup scheme.

## Overview

Optimized for Archlinux, this role is a key component of a comprehensive backup system. It works in conjunction with other roles to ensure that backup data is collected, verified, and maintained. The role uses a Bash script to pull backups, manage remote connections, and handle incremental backup creation.

## Purpose

Backup Remote to Local provides a robust solution for retrieving backup data from remote servers. By leveraging rsync, it creates incremental backups that support both file and database recovery. This ensures the integrity and security of your backup data across distributed environments.

## Features

- **Remote Backup Retrieval:** Pulls backups from a remote server using secure SSH connections.
- **Incremental Backup with rsync:** Uses rsync with options for archive, backup, and hard linking to efficiently manage changes.
- **Retry Logic:** Implements a retry mechanism to handle transient network issues or remote errors.
- **Integration with Other Roles:** Works alongside roles like sys-svc-directory-validator, sys-ctl-cln-faild-bkps, sys-timer, sys-bkp-provider, and sys-lock.

## Further Resources

- [How I backup dedicated root servers](https://blog.veen.world/2020/12/26/how-i-backup-dedicated-root-servers/)

## Credits

Developed and maintained by **Kevin Veen-Birkenbach**.
Learn more at [veen.world](https://www.veen.world).
Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code).
Licensed under the [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license).
