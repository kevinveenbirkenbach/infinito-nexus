#!/bin/sh
set -eu

# Paths / constants
APP_ROOT="/var/www/html"
MARKER="$APP_ROOT/.infinito/installed"

cd "$APP_ROOT"
mkdir -p "$APP_ROOT/.infinito"

echo "[INIT] Checking database via PDO..."
php -r '
$url = getenv("DATABASE_URL");
if (!$url) { fwrite(STDERR, "DATABASE_URL not set\n"); exit(1); }
$p = parse_url($url);
if (!$p || !isset($p["scheme"])) { fwrite(STDERR, "Invalid DATABASE_URL\n"); exit(1); }
$scheme = $p["scheme"];
if ($scheme === "mysql" || $scheme === "mariadb") {
  $host = $p["host"] ?? "localhost";
  $port = $p["port"] ?? 3306;
  $db   = ltrim($p["path"] ?? "", "/");
  $user = $p["user"] ?? "";
  $pass = $p["pass"] ?? "";
  $dsn  = "mysql:host=".$host.";port=".$port.";dbname=".$db.";charset=utf8mb4";
} else {
  fwrite(STDERR, "Unsupported DB scheme: ".$scheme."\n"); exit(1);
}
$retries = 60;
while ($retries-- > 0) {
  try { $pdo = new PDO($dsn, $user, $pass, [PDO::ATTR_TIMEOUT => 3]); exit(0); }
  catch (Exception $e) { sleep(2); }
}
fwrite(STDERR, "DB not reachable\n"); exit(1);
'

if [ ! -f "$MARKER" ]; then
  echo "[INIT] Checking if database is empty..."
  # PHP exits: 0 = empty, 100 = non-empty, 1 = error
  if php -r '
    $url = getenv("DATABASE_URL");
    $p   = parse_url($url);
    $db  = ltrim($p["path"] ?? "", "/");
    $dsn = "mysql:host=".($p["host"]??"localhost").";port=".($p["port"]??3306).";dbname=".$db.";charset=utf8mb4";
    try {
      $pdo = new PDO($dsn, $p["user"] ?? "", $p["pass"] ?? "");
      $q = $pdo->query("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=".$pdo->quote($db));
      $cnt = (int)$q->fetchColumn();
      if ($cnt === 0) { exit(0); } else { exit(100); }
    } catch (Exception $e) { fwrite(STDERR, $e->getMessage()."\n"); exit(1); }
  '; then
    DBCHK=0
  else
    DBCHK=$?
  fi

  if [ "$DBCHK" -eq 0 ]; then
    echo "[INIT] Installing Shopware (empty DB detected)..."
    # IMPORTANT: no --force; let Shopware run its internal steps only on empty DB
    php -d memory_limit=1024M bin/console system:install --basic-setup --create-database
  elif [ "$DBCHK" -eq 100 ]; then
    echo "[INIT] Database is not empty -> skipping system:install"
  else
    echo "[INIT] Database check failed (code $DBCHK)"; exit 1
  fi

  # Safe to run (no-ops when up-to-date)
  php -d memory_limit=1024M bin/console database:migrate --all || true
  php -d memory_limit=1024M bin/console database:migrate-destructive --all || true

  # Housekeeping
  php bin/console cache:clear || true
  php bin/console dal:refresh:index || true

  # Marker + perms
  touch "$MARKER"
  chown -R www-data:www-data "$APP_ROOT"

  echo "[INIT] Done."
else
  echo "[INIT] Marker found, skipping install."
fi
