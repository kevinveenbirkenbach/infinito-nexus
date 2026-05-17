#!/usr/bin/env bash
#
# Verify a Friendica addon's _install() hooks are present in the `hook` DB
# table. `bin/console addon enable` only ever writes the config[addons.<X>]
# entry; the `_install` function runs in the same PHP process but its
# Hook::register() calls have empirically been observed to leave the `hook`
# table empty on the first deploy of a fresh stack. A disable+enable cycle
# from a clean shell at any later point fixes it. Run this verifier after
# `sync_addon.sh` so the broken state fails the role instead of surfacing
# as a silent login regression at the Playwright stage.
#
# Usage:
#   verify_addon_hooks.sh EXEC_PREFIX ADDON MIN_HOOKS
#     EXEC_PREFIX  full `docker compose exec ... friendica` invocation as a
#                  single arg (no trailing `bin/console`)
#     ADDON        addon name (e.g. ldapauth)
#     MIN_HOOKS    minimum number of rows expected in `hook` for this addon
#                  (e.g. 2 for ldapauth's load_config + authenticate)
#
# On mismatch, the script runs one disable+enable cycle through bin/console
# and re-checks. If hooks are still missing it exits non-zero.
set -euo pipefail

EXEC="$1"
ADDON="$2"
MIN_HOOKS="$3"

CONSOLE="$EXEC /var/www/html/bin/console"

count_hooks() {
    $EXEC php -d display_errors=0 -r '
        require "/var/www/html/vendor/autoload.php";
        $cfg = include "/var/www/html/config/local.config.php";
        $db = $cfg["database"];
        $h = explode(":", $db["hostname"]);
        $dsn = "mysql:host=" . $h[0] . ";port=" . ($h[1] ?? 3306) . ";dbname=" . $db["database"];
        $pdo = new PDO($dsn, $db["username"], $db["password"]);
        $s = $pdo->prepare("SELECT COUNT(*) FROM hook WHERE file LIKE :p");
        $s->execute([":p" => "%addon/" . $argv[1] . "/" . $argv[1] . ".php"]);
        echo (int) $s->fetchColumn();
    ' -- "$ADDON" 2>/dev/null
}

count="$(count_hooks)"
if [ "${count:-0}" -ge "$MIN_HOOKS" ]; then
    echo "[verify_addon_hooks] $ADDON hooks=$count (>= $MIN_HOOKS, OK)"
    exit 0
fi

echo "[verify_addon_hooks] $ADDON hooks=$count (< $MIN_HOOKS); re-cycling disable+enable"
$CONSOLE addon disable "$ADDON" 2>&1 || true
$CONSOLE addon enable  "$ADDON" 2>&1 || true

count="$(count_hooks)"
if [ "${count:-0}" -ge "$MIN_HOOKS" ]; then
    echo "[verify_addon_hooks] $ADDON hooks=$count after re-cycle (>= $MIN_HOOKS, OK)"
    exit 0
fi

echo "[verify_addon_hooks] $ADDON hooks=$count after re-cycle (still < $MIN_HOOKS)" >&2
exit 1
