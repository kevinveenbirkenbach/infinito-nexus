# Core Daemon Role

This Ansible role handles resetting and cleaning up “Infinito.Nexus” systemd service units for the core daemon.

## Description

When enabled via the `MODE_RESET` flag, this role will:

1. Run its reset tasks exactly once per play (`run_once_sys_rst_daemon` guard).  
2. Find all `/etc/systemd/system/*.infinito.service` units.  
3. Stop and disable each unit.  
4. Remove the unit files.  
5. Reload the systemd daemon.

## License

This role is released under the Infinito.Nexus NonCommercial License (CNCL).
See [license details](https://s.infinito.nexus/license)

## Author Information

Kevin Veen-Birkenbach
Consulting & Coaching Solutions
[https://www.veen.world](https://www.veen.world)