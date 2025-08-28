<?php
/**
 * System plugin that auto-creates a Joomla user after successful LDAP authentication.
 * It reads the LDAP Auth plugin params from #__extensions (folder=authentication, element=ldap),
 * looks up cn/mail for the authenticated uid, and creates a local Joomla user if missing.
 */

defined('_JEXEC') || die;

use Joomla\CMS\Factory;
use Joomla\CMS\Plugin\CMSPlugin;
use Joomla\CMS\User\User;
use Joomla\Database\DatabaseDriver;
use Joomla\Authentication\Authentication;

class PlgSystemLdapautocreate extends CMSPlugin
{
    protected $app;

    /**
     * Runs after authentication handlers; fires for both frontend and backend.
     * @param array $options Contains 'username' and more after auth
     * @return void
     */
    public function onUserAfterAuthenticate($options, $response)
    {
        // Only proceed on success
        if (($response->status ?? null) !== Authentication::STATUS_SUCCESS) {
            return;
        }

        $username = $response->username ?? $options['username'] ?? null;
        if (!$username) {
            return;
        }

        /** @var DatabaseDriver $dbo */
        $dbo = Factory::getDbo();

        // If user already exists locally, nothing to do
        $exists = (int) $dbo->setQuery(
            $dbo->getQuery(true)
                ->select('COUNT(*)')
                ->from($dbo->quoteName('#__users'))
                ->where($dbo->quoteName('username') . ' = ' . $dbo->quote($username))
        )->loadResult();

        if ($exists) {
            return;
        }

        // Read LDAP Auth plugin params to connect (the ones we configured via cli-ldap.php)
        $ldapExt = $dbo->setQuery(
            $dbo->getQuery(true)
                ->select('*')
                ->from($dbo->quoteName('#__extensions'))
                ->where($dbo->quoteName('type') . " = 'plugin'")
                ->where($dbo->quoteName('folder') . " = 'authentication'")
                ->where($dbo->quoteName('element') . " = 'ldap'")
        )->loadObject();

        if (!$ldapExt) {
            return; // LDAP plugin not found; bail out silently
        }

        $p = json_decode($ldapExt->params ?: "{}", true) ?: [];
        $host   = $p['host'] ?? 'openldap';
        $port   = (int) ($p['port'] ?? 389);
        $baseDn = $p['base_dn'] ?? '';
        $bindDn = $p['username'] ?? '';
        $bindPw = $p['password'] ?? '';
        $attrUid = $p['ldap_uid'] ?? 'uid';
        $attrMail = $p['ldap_email'] ?? 'mail';
        $attrName = $p['ldap_fullname'] ?? 'cn';

        // Look up user in LDAP to fetch name/email
        $ds = @ldap_connect($host, $port);
        if (!$ds) { return; }
        ldap_set_option($ds, LDAP_OPT_PROTOCOL_VERSION, 3);
        @ldap_bind($ds, $bindDn, $bindPw);

        $filter = sprintf('(%s=%s)', $attrUid, ldap_escape($username, '', LDAP_ESCAPE_FILTER));
        $sr = @ldap_search($ds, $baseDn, $filter, [$attrName, $attrMail]);
        $entry = $sr ? @ldap_first_entry($ds, $sr) : null;

        $name  = $entry ? (@ldap_get_values($ds, $entry, $attrName)[0] ?? $username) : $username;
        $email = $entry ? (@ldap_get_values($ds, $entry, $attrMail)[0] ?? ($username.'@example.invalid')) : ($username.'@example.invalid');

        if ($ds) { @ldap_unbind($ds); }

        // Create Joomla user (Registered group id=2)
        $data = [
            'name'     => $name,
            'username' => $username,
            'email'    => $email,
            // Password is irrelevant for LDAP; set a random one
            'password' => bin2hex(random_bytes(12)),
            'block'    => 0,
            'groups'   => [2],
        ];

        $user = new User;
        if (!$user->bind($data)) {
            return;
        }
        $user->save();
    }
}
