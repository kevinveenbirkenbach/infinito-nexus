# Cleanup Failed Backups

This role installs and runs the **cleanback** CLI to validate and delete **failed Docker backups** under `/Backups/*/backup-docker-to-local`.  
Validation is performed via `dirval`; failures can be removed automatically in a non-interactive service execution.
