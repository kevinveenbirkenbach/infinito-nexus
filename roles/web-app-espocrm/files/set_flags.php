<?php
/**
 * set_flags.php – Ensure EspoCRM runtime flags are set idempotently.
 */

require "/var/www/html/bootstrap.php";

$app = new \Espo\Core\Application();
$c   = $app->getContainer();
$cfg = $c->get("config");
$w   = $c->get("injectableFactory")->create("\Espo\Core\Utils\Config\ConfigWriter");

// Read from ENV
$flags = [
    "maintenanceMode" => in_array(strtolower(getenv("ESPO_INIT_MAINTENANCE_MODE") ?: "false"), ["1","true","yes","on"]),
    "cronDisabled"    => in_array(strtolower(getenv("ESPO_INIT_CRON_DISABLED") ?: "false"), ["1","true","yes","on"]),
    "useCache"        => in_array(strtolower(getenv("ESPO_INIT_USE_CACHE") ?: "true"), ["1","true","yes","on"])
];

$changed = false;
foreach ($flags as $k => $v) {
    if ($cfg->get($k) !== $v) {
        $w->set($k, $v);
        $changed = true;
    }
}

if ($changed) {
    $w->save();
    echo "CHANGED\n";
} else {
    echo "UNCHANGED\n";
}
