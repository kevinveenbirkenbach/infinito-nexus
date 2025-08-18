# Backup Remote to Local

## Description

This role pulls backups from a remote server and stores them locally using rsync with retry logic. It is designed to retrieve remote backup data and integrate with your overall backup scheme.

## Overview

Optimized for Archlinux, this role is a key component of a comprehensive backup system. It works in conjunction with other roles to ensure that backup data is collected, verified, and maintained. The role uses a Bash script to pull backups, manage remote connections, and handle incremental backup creation.

## Purpose

Backup Remote to Local is a robust solution for retrieving backup data from remote servers. By leveraging rsync, it creates incremental backups that support both file and database recovery. This ensures the integrity and security of your backup data across distributed environments.

## Features

- **Remote Backup Retrieval:** Pulls backups from a remote server using secure SSH connections.
- **Incremental Backup with rsync:** Uses rsync with options for archive, backup, and hard linking to efficiently manage changes.
- **Retry Logic:** Implements a retry mechanism to handle transient network issues or remote errors.
- **Integration with Other Roles:** Works alongside roles like sys-svc-directory-validator, sys-ctl-cln-faild-bkps, sys-timer, sys-bkp-provider, and sys-lock.
- **Administrative Debugging:** Detailed debug instructions and administrative tasks are provided in a separate file.

## Other Resources

- **Backup Scheme:**  
  ![backup scheme](https://blog.veen.world/wp-content/uploads/2020/12/srv-backup-768x567.jpg)  
  More details can be found in [this blog post](https://blog.veen.world/2020/12/26/how-i-backup-dedicated-root-servers/).

## Administration & Debugging

For detailed debug instructions and administrative tasks, please refer to the [Administration Tasks](Administration.md) file.
