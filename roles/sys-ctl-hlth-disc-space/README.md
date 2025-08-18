# sys-ctl-hlth-disc-space

## Description
Monitors disk-space usage and alerts if any filesystem usage exceeds your defined threshold.

## Features
- Uses `df` to gather current usage.
- Compares against `size_percent_disc_space_warning` threshold.
- Sends failure alerts via `sys-ctl-alm-compose`.
- Runs on a configurable systemd timer.
