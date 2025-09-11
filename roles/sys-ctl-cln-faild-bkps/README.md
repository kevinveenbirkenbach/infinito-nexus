# Cleanup Failed Backups

This role installs and runs the **cleanback** CLI to validate and delete **failed Docker backups** under `/Backups/*/backup-docker-to-local`.  
Validation is performed via `dirval`; failures can be removed automatically in a non-interactive service execution.

## Behavior
- Installs `cleanback` via `pkgmgr`.
- Runs `cleanback` (`main.py`) as a **systemd oneshot** service.
- Executes `--all` with `--yes` so failing directories are deleted automatically.
- **No defaults** for runtime knobs:
  - `CLEANBACK_TIMEOUT_SECONDS` (required)
  - `SYS_SCHEDULE_CLEANUP_FAILED_BACKUPS` (required)
- **Workers** (`CLEANUP_FAILED_BACKUPS_WORKERS`) are **derived from Ansible facts only** (no arbitrary defaults). Facts **must** be gathered.
