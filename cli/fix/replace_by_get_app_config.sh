#!/usr/bin/env bash
set -euo pipefail

# Just a little refactoring script, you can delete it later
ATTR="$1"
OLD="applications[application_id].$ATTR"
NEW="applications | get_app_conf(application_id, '$ATTR', True)"
bsr ./ "$OLD" -rFfc -n "$NEW"
