<?php
/**
 * System plugin that auto-creates a Joomla user after successful LDAP authentication.
 * Now with structured logging (enable via JOOMLA_LDAP_AUTOCREATE_LOG=1).
 */

defined('_JEXEC') || die;

use Joomla\CMS\Factory;
use Joomla\CMS\Plugin\CMSPlugin;
use Joomla\CMS\User\User;
use Joomla\Authentication\Authentication;
use Joomla\CMS\Log\Log;

class PlgSystemLdapautocreate extends CMSPlugin
{
    protected $app;
    private bool $logEnabled = false;

    public function __construct(&$subject, $config)
    {
        parent::__construct($subject, $config);

        // Enable logger only when explicitly requested
        $this->logEnabled = (bool) filter_var(getenv('JOOMLA_LDAP_AUTOCREATE_LOG') ?: '0', FILTER_VALIDATE_BOOL);

        if ($this->logEnabled) {
            // Register a dedicated channel and file
            Log::addLogger(
                ['text_file' => 'ldapauth.log', 'extension' => 'plg_system_ldapautocreate'],
                Log::ALL,
                ['ldapautocreate']
            );
            $this->log('logger-initialized', ['version' => '1.0.0']);
        }
    }

    private function log(string $event, array $ctx = []): void
    {
        if (!$this->logEnabled) {
            return;
        }
        $payload = json_encode(['event' => $event, 'ctx' => $ctx], JSON_UNESCAPED_SLASHES);
        Log::add($payload, Log::INFO, 'ldapautocreate');
    }

    /**
     * Fires after authentication handlers; frontend and backend.
     * @param array $options
     * @param object $response  ->status, ->type, ->error_message, ->username, etc.
     */
    public function onUserAfterAuthenticate($options, $response)
    {
        // Defensive: normalize shape
        $status = $response->status ?? null;
        $type   = $response->type ?? '(unknown)';
        $user   = $response->username ?? ($options['username'] ?? null);

        $this->log('after-auth-enter', [
            'username' => $user,
            'status'   => $status,
            'type'     => $type,
            'error'    => $response->error_message ?? null,
        ]);

        // Only proceed when LDAP (or any plugin) actually succeeded
        if ($status !== Authentication::STATUS_SUCCESS) {
            $this->log('skip-non-success', ['reason' => 'status!=' . Authentication::STATUS_SUCCESS]);
            return;
        }

        if (!$user) {
            $this->log('skip-missing-username');
            return;
        }

        // If user exists locally, nothing to do
        $dbo = Factory::getDbo();
        $count = (int) $dbo->setQuery(
            $dbo->getQuery(true)
                ->select('COUNT(*)')
                ->from($dbo->quoteName('#__users'))
                ->where($dbo->quoteName('username') . ' = ' . $dbo->quote($user))
        )->loadResult();

        if ($count > 0) {
            $this->log('user-exists', ['username' => $user]);
            return;
        }

        // Read LDAP plugin params (host/port/base_dn/attrs) and fetch cn/mail
        $ldapExt = $dbo->setQuery(
            $dbo->getQuery(true)
                ->select('*')
                ->from($dbo->quoteName('#__extensions'))
                ->where("type='plugin' AND folder='authentication' AND element='ldap'")
        )->loadObject();

        if (!$ldapExt) {
            $this->log('ldap-plugin-missing');
            return;
        }

        $p = json_decode($ldapExt->params ?: "{}", true) ?: [];
        $host     = $p['host'] ?? 'openldap';
        $port     = (int) ($p['port'] ?? 389);
        $baseDn   = $p['base_dn'] ?? '';
        $bindDn   = $p['username'] ?? '';
        $bindPw   = $p['password'] ?? '';
        $attrUid  = $p['ldap_uid'] ?? 'uid';
        $attrMail = $p['ldap_email'] ?? 'mail';
        $attrName = $p['ldap_fullname'] ?? 'cn';

        $this->log('ldap-params', [
            'host' => $host, 'port' => $port, 'base_dn' => $baseDn,
            'attrUid' => $attrUid, 'attrMail' => $attrMail, 'attrName' => $attrName,
        ]);

        $ds = @ldap_connect($host, $port);
        if (!$ds) { $this->log('ldap-connect-failed'); return; }
        ldap_set_option($ds, LDAP_OPT_PROTOCOL_VERSION, 3);
        @ldap_bind($ds, $bindDn, $bindPw);

        $filter = sprintf('(%s=%s)', $attrUid, ldap_escape($user, '', LDAP_ESCAPE_FILTER));
        $sr = @ldap_search($ds, $baseDn, $filter, [$attrName, $attrMail]);
        $entry = $sr ? @ldap_first_entry($ds, $sr) : null;

        $name  = $entry ? (@ldap_get_values($ds, $entry, $attrName)[0] ?? $user) : $user;
        $email = $entry ? (@ldap_get_values($ds, $entry, $attrMail)[0] ?? ($user.'@example.invalid')) : ($user.'@example.invalid');

        if ($ds) { @ldap_unbind($ds); }

        $this->log('creating-user', ['username' => $user, 'name' => $name, 'email' => $email]);

        // Create Joomla user in Registered (id=2)
        $data = [
            'name'     => $name,
            'username' => $user,
            'email'    => $email,
            'password' => bin2hex(random_bytes(12)),
            'block'    => 0,
            'groups'   => [2],
        ];

        $joomUser = new User;
        if (!$joomUser->bind($data)) {
            $this->log('user-bind-failed', ['error' => 'bind() returned false']);
            return;
        }

        if (!$joomUser->save()) {
            $this->log('user-save-failed', ['error' => 'save() returned false']);
            return;
        }

        $this->log('user-created', ['id' => $joomUser->id, 'username' => $user]);
    }
}
