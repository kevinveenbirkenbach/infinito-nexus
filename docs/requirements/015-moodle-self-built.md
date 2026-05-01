# 015 — Self-built Moodle image (replaces `bitnamilegacy/moodle`)

## User Story

As an operator deploying `web-app-moodle`, I want the role to build
its own Moodle container image from upstream Moodle source on top of
the official PHP-FPM container, so that the deployment no longer
depends on the discontinued `bitnamilegacy/moodle` image and stays on
the latest supported Moodle version with a transparent, auditable
build pipeline.

## Background

`web-app-moodle` currently builds on `bitnamilegacy/moodle:4.5`. The
image lineage is the legacy mirror of Bitnami's discontinued Moodle
container line. It pins the runtime to Bitnami's opaque
`/opt/bitnami/moodle` layout, the `daemon` user, the
`install_packages` helper, and a bespoke env-driven entrypoint that
generates `config.php`. The legacy mirror does not receive new tags
beyond the snapshot Bitnami left behind, so newer Moodle releases
(4.6, 5.x) are unreachable through it. The role needs to migrate to
an image we build ourselves from upstream Moodle source.

Moodle's own developer documentation lists official container images
at <https://moodledev.io/general/app/development/setup/docker-images>.
The "Moodle App" images published there are scoped to the React
Native mobile client, NOT the PHP web application this role deploys.
Upstream therefore does not ship a maintained PHP-FPM Moodle web
image we can consume directly; the closest reference Dockerfiles live
under <https://github.com/moodlehq/moodle-docker> and are scoped to
core development workflows (PHPUnit, Behat, plugin testing) rather
than production-style deployment. This requirement bases the new
image on the **official `php:<latest>-fpm` image** and adapts the
relevant pieces from `moodlehq/moodle-docker` (extension list, Apache
↔ nginx vhost shape, cron expectations) instead of vendoring the full
moodle-docker layout, which carries dev-only extras the production
deployment does not need.

The role keeps everything the operator already relies on:

- shared-service wiring (oidc, logout, dashboard, matomo, email,
  mariadb, prometheus) via [meta/services.yml](../../roles/web-app-moodle/meta/services.yml),
- the OIDC plugin install path (microsoft/moodle-auth_oidc) baked
  into the build,
- the post-deploy CLI configuration tasks under
  [tasks/03_oidc.yml](../../roles/web-app-moodle/tasks/03_oidc.yml).

## Identity-integration variants

The role MUST ship a `meta/variants.yml` with two variants exercising
the two supported identity-integration shapes. The matrix-deploy
mechanism described in [variants.md](../contributing/design/variants.md)
runs them in order during a full-cycle deploy.

| Variant | Login auth          | Live attribute sync | Use case                                                                 |
| ------- | ------------------- | ------------------- | ------------------------------------------------------------------------ |
| **0**   | `auth_oidc` (Keycloak SSO) | `auth_ldap` sync-only (cron-driven) + `auth_oidc` per-login refresh | Default deployment. SSO via Keycloak; LDAP cron sync keeps `mdl_user` live without requiring re-login. |
| **1**   | `auth_ldap` (direct LDAP bind) | `auth_ldap` sync-only (cron-driven) | LDAP-only deployment for tenants that intentionally do NOT run Keycloak/OIDC against Moodle. Validates that the role works end-to-end without the OIDC shared service. |

In both variants, **LDAP is the canonical attribute store** and the
Moodle ↔ LDAP plumbing is identical: Moodle's `auth_ldap` plugin runs
its sync task on Moodle cron and pulls every mapped attribute
listed in [Profile-field mapping](#profile-field-mapping-keycloak-↔-ldap-↔-moodle).
The variants differ only in the **login** path and in whether
Keycloak is part of the topology at all.

### Variant 0 — `auth_oidc` + `auth_ldap` sync-only (hybrid)

- [ ] `auth_oidc` is enabled and set as the **primary login method**
      (`config_plugin auth_oidc`, plus `auth = 'oidc,ldap'` global
      setting with `oidc` listed first).
- [ ] `auth_ldap` is enabled but **NOT** as a login method visible
      to users; it loads only so its sync task runs on cron. The
      role MUST NOT show "LDAP server" as a login option in the
      Moodle login page (`auth_ldap.config.removecontexts` /
      `loginpage_idp_list` MUST suppress it).
- [ ] `auth_ldap`'s sync task (`\auth_ldap\task\sync_task`) MUST be
      registered in Moodle's scheduled tasks at an interval ≤
      15 minutes by default; the role MUST set the interval via
      `auth_ldap.config.task_minutes` (or the equivalent cron-task
      override) so a fresh deploy converges to the documented
      cadence without operator intervention.
- [ ] `auth_oidc` field-mapping is configured per
      [Moodle `auth_oidc` field mapping](#moodle-auth_oidc-field-mapping):
      every claim in the mapping table updates `mdl_user` /
      Custom Profile Fields on every login.
- [ ] `auth_ldap` field-mapping mirrors the same Moodle-↔-LDAP
      column pairing: every "LDAP attribute" cell in the mapping
      table is bound to its Moodle field via
      `auth_ldap.config.field_map_<moodle-col>` =
      `<ldap-attribute>` and `auth_ldap.config.field_lock_<moodle-col>`
      = `locked` so Moodle stays read-only for the attribute
      (per the
      [source-of-truth hierarchy](#source-of-truth-hierarchy);
      the only write surface is the Keycloak Account Console).
- [ ] Conflict resolution between the two plugins MUST be
      "last-update-wins" against the same canonical LDAP source,
      and the role MUST document this in the Moodle
      `Administration.md` so an operator knows why both plugins
      mutate the same row.
- [ ] On idempotent re-deploy, both `auth_oidc` and `auth_ldap`
      configuration MUST report `changed=0`.

### Variant 1 — `auth_ldap` only (no OIDC)

- [ ] `auth_oidc` is **disabled** (`disable_plugin auth_oidc`),
      and `services.oidc.enabled` in this variant's
      `meta/variants.yml` block MUST be `false` so the
      shared-service plumbing does NOT add the role to Keycloak's
      client list.
- [ ] `auth_ldap` is the **primary login method** (`auth = 'ldap'`).
      Users authenticate by submitting their LDAP `uid` + password
      to Moodle's login form; Moodle binds against the LDAP
      server with the supplied credentials.
- [ ] LDAP server connection settings (`auth_ldap.config.host_url`,
      `bind_dn`, `bind_pw`, `contexts`, `user_attribute`,
      `objectclass`) MUST be rendered from the same shared LDAP
      service definition that variant 0 federates from Keycloak,
      so both variants point at the same backend without
      duplicating the connection contract.
- [ ] `auth_ldap` field-mapping uses the same Moodle-↔-LDAP
      column pairing as variant 0; sync_task runs on the same
      cadence.
- [ ] `web-svc-logout` integration MUST still apply (Moodle's
      logout flow ends the user's session and redirects to the
      shared logout endpoint), even though the upstream IdP is
      not Keycloak. The role MUST document the post-logout
      redirect path that applies in this variant.
- [ ] On idempotent re-deploy, the LDAP-only configuration MUST
      report `changed=0`.

## Naming

- Image build context lives in
  `roles/web-app-moodle/templates/Dockerfile.j2`.
- Built image tag follows the existing custom-image convention:
  `{{ entity_name }}_custom`.
- Container name stays `moodle` (per
  [meta/services.yml](../../roles/web-app-moodle/meta/services.yml)).

## Acceptance Criteria

### Image base

- [ ] The Dockerfile starts from **`php:8.3-fpm`** (the highest
      Moodle-supported PHP minor at the time of writing; PHP 8.4
      is candidate-status for the targeted Moodle line and is
      explicitly NOT used). When upstream Moodle promotes a
      newer PHP minor to "fully supported", the role MAY be
      bumped in a follow-up; this requirement does NOT
      auto-track PHP-version drift.
- [ ] The Dockerfile MUST NOT rely on Bitnami helpers
      (`install_packages`, `BITNAMI_*` paths, `daemon` user). System
      packages MUST be installed via `apt-get install --no-install-recommends`
      with `apt-get clean && rm -rf /var/lib/apt/lists/*` to keep the
      image lean.
- [ ] The PHP extension set required by the targeted Moodle release
      MUST be installed via `docker-php-ext-install` /
      `docker-php-ext-enable` (or equivalent for ext-pgsql,
      ext-intl, ext-gd, ext-xml, ext-mbstring, ext-mysqli, ext-zip,
      ext-soap, ext-curl, ext-exif, ext-opcache, ext-fileinfo,
      ext-ldap). The exact set MUST match the upstream Moodle
      "Server requirements" page for the pinned version.
- [ ] OPcache is configured with Moodle's recommended production
      settings (`opcache.memory_consumption`, `interned_strings_buffer`,
      `max_accelerated_files`, `revalidate_freq=60`, `validate_timestamps=1`).

### Moodle source

- [ ] The Moodle source MUST be fetched at build time from the
      **floating** stable endpoint
      `https://download.moodle.org/download.php/direct/stable<MAJOR><MINOR>/moodle-latest-<MAJOR><MINOR>.tgz`
      against the latest stable major.minor that Moodle officially
      publishes (e.g. `stable50/moodle-latest-50.tgz` for the 5.0
      stable line). The tarball is intentionally **floating**, NOT
      pinned to an exact patch version; this means a `make build`
      always lands the most recent stable patch in that branch.
- [ ] The download MUST be checksum-verified against the
      `moodle-latest-<MAJOR><MINOR>.tgz.sha256` file published
      next to the tarball, so a corrupted or substituted tarball
      aborts the build deterministically. The SHA file is
      re-fetched on every build (no caching) so the floating
      tarball cannot drift from its published hash.
- [ ] Moodle's source tree MUST be extracted to `/var/www/html`
      (standard php-fpm web root). The role MUST NOT introduce a
      Bitnami-style `/opt/bitnami/moodle` ↔ `/bitnami/moodle`
      symlink.
- [ ] The `moodledata` directory MUST live at `/var/www/moodledata`
      (matches Moodle's documented "outside the web root"
      convention) and MUST be writable by the runtime user.
- [ ] Ownership of `/var/www/html` and `/var/www/moodledata` is
      `www-data:www-data` after build.

### OIDC plugin baked in

- [ ] The Microsoft `moodle-auth_oidc` plugin MUST be installed
      under `auth/oidc/` of the Moodle code tree at build time when
      `MOODLE_OIDC_ENABLED` is true.
- [ ] The plugin tag MUST be selected from the GitHub releases of
      `microsoft/moodle-auth_oidc` matching the Moodle major.minor
      (existing logic in
      [Dockerfile.j2](../../roles/web-app-moodle/templates/Dockerfile.j2)
      `curl https://api.github.com/repos/.../tags`). The selection
      logic stays, but its install path moves from
      `BITNAMI_OIDC_PLUGIN_DIR` to `<moodle_code>/auth/oidc/`.

### Cron sidecar

Moodle relies on a cron loop (`php admin/cli/cron.php`) for
scheduled tasks (`auth_ldap` sync, session cleanup, message
queue, course completion, etc.). The PHP-FPM image does NOT run
cron natively, so the role MUST add a dedicated sidecar.

- [ ] A `cron` service in
      [compose.yml.j2](../../roles/web-app-moodle/templates/compose.yml.j2)
      MUST run alongside the PHP-FPM and nginx containers. It
      reuses the same custom-built image (`{{ entity_name }}_custom`)
      with a `command:` that invokes `php /var/www/html/admin/cli/cron.php`
      in a loop with a sleep interval bounded by Moodle's
      shortest scheduled-task cadence (≤ 60s).
- [ ] The cron container MUST mount the same `code` and `data`
      named volumes as the FPM container, read-write, so it sees
      the same Moodle source tree and `moodledata` writes.
- [ ] The cron container MUST run as `www-data:www-data` and
      MUST NOT publish any port.
- [ ] On startup, the cron container MUST wait for the FPM
      container's healthcheck before invoking `cron.php` for
      the first time, so a freshly initialised database is not
      hit by an unfinished install. The compose `depends_on`
      with `condition: service_healthy` covers this.

### Web server

- [ ] The role MUST add a sidecar `nginx` service in
      [compose.yml.j2](../../roles/web-app-moodle/templates/compose.yml.j2)
      that fronts the PHP-FPM container. The nginx container uses
      the official `nginx:<X>-alpine` image.
- [ ] The nginx vhost configuration is rendered from a Jinja2
      template under
      `roles/web-app-moodle/templates/nginx-moodle.conf.j2` and
      mounted into the nginx container at
      `/etc/nginx/conf.d/default.conf`. The vhost MUST implement
      Moodle's official nginx recipe
      (<https://docs.moodle.org/en/Nginx>): `try_files $uri =404`,
      `fastcgi_split_path_info`, `fastcgi_pass <fpm-container>:9000`,
      `fastcgi_index index.php`, and a `client_max_body_size` that
      matches `upload_max_filesize` in the PHP container.
- [ ] The PHP-FPM container exposes port 9000 only on the compose
      internal network; only the nginx container publishes the HTTP
      port that the front-proxy consumes.
- [ ] The published HTTP port (`{{ ports.local.http }}`) MUST stay
      bound to `DOCKER_BIND_HOST` (no change vs. the existing role).

### Runtime configuration via env-driven entrypoint

- [ ] The image ships a custom entrypoint
      `roles/web-app-moodle/templates/entrypoint.sh.j2` (rendered
      into the build context, ADDed by the Dockerfile, marked
      executable, set as the FPM container's `ENTRYPOINT`).
- [ ] On every container start, the entrypoint MUST render
      `<moodle_code>/config.php` from environment variables passed
      in via [env.j2](../../roles/web-app-moodle/templates/env.j2).
      Variables MUST cover:
  - site URL (`wwwroot`),
  - DB type / host / port / name / user / password / prefix,
  - data root (`dataroot`),
  - admin email (`supportemail`, `siteadmins`),
  - SMTP (host, port, user, password, secure mode),
  - reverse-proxy + SSL flags (`sslproxy=true`, `reverseproxy=true`),
  - debug mode (`debug=DEBUG_DEVELOPER` only when `MODE_DEBUG=true`,
    `debug=DEBUG_NONE` otherwise).
- [ ] After rendering, the entrypoint MUST chown
      `<moodle_code>/config.php` and `/var/www/moodledata` to
      `www-data:www-data` and exec `php-fpm` as the Docker `CMD`.
- [ ] If `<moodle_code>/config.php` already exists from a previous
      run (persisted via the code volume), the entrypoint MUST
      regenerate it from env (so env changes always apply) but
      MUST NOT clobber pre-existing site state under
      `/var/www/moodledata`.

### Volumes & persistence

- [ ] [meta/services.yml](../../roles/web-app-moodle/meta/services.yml)
      declares two named volumes: `code` (Moodle code tree) and
      `data` (moodledata). The `volumes:` block in
      [compose.yml.j2](../../roles/web-app-moodle/templates/compose.yml.j2)
      MUST mount them at `/var/www/html` and `/var/www/moodledata`
      respectively.
- [ ] Volume names MUST be **fresh** under the new role
      (e.g. `web-app-moodle_code`, `web-app-moodle_data`) and
      MUST NOT reuse the legacy `bitnami_*` volume names from
      the old role. Operators upgrading from the Bitnami image
      MUST start from a fresh deploy of `web-app-moodle`; the
      role MUST NOT ship a migration path that reads from the
      legacy `bitnami_moodle_*` volumes. The
      [README](../../roles/web-app-moodle/README.md) MUST
      document this fresh-deploy precondition explicitly.
- [ ] On first start, the entrypoint copies the baked code tree
      (`/var/www/html` from the image) into the persistent code
      volume only when the volume is empty, so subsequent restarts
      keep operator-installed plugins.

### Role tasks

- [ ] [vars/main.yml](../../roles/web-app-moodle/vars/main.yml)
      drops every `BITNAMI_*` variable. Replacements live under
      `MOODLE_CODE_DIR=/var/www/html`,
      `MOODLE_DATA_DIR=/var/www/moodledata`,
      `MOODLE_OIDC_PLUGIN_DIR=/var/www/html/auth/oidc`,
      `MOODLE_RUNTIME_USER=www-data:www-data`.
- [ ] [tasks/02_ownership.yml](../../roles/web-app-moodle/tasks/02_ownership.yml)
      uses the new paths and the `www-data:www-data` user.
- [ ] [tasks/03_oidc.yml](../../roles/web-app-moodle/tasks/03_oidc.yml)
      replaces `/opt/bitnami/moodle/admin/cli/...` invocations with
      `/var/www/html/admin/cli/...` and runs them as `www-data`
      (e.g. `container exec --user www-data {{ MOODLE_CONTAINER }}
      php /var/www/html/admin/cli/cfg.php …`).
- [ ] [tasks/01_patch_config.yml](../../roles/web-app-moodle/tasks/01_patch_config.yml)
      is reviewed and either rewritten against the new
      env-rendered `config.php` shape or removed if the entrypoint
      already covers its scope.

### Documentation

- [ ] [README.md](../../roles/web-app-moodle/README.md) updates the
      Source / Image section: the Bitnami reference is replaced
      with a link to this requirement and to
      <https://moodledev.io/general/app/development/setup/docker-images>.
- [ ] [Administration.md](../../roles/web-app-moodle/Administration.md)
      replaces every `/opt/bitnami/moodle` and `/bitnami/moodledata`
      path with the new locations and replaces the `daemon` user
      with `www-data`.
- [ ] [TODO.md](../../roles/web-app-moodle/TODO.md) drops the
      Bitnami-issue link or restates the residual concern against
      the new image (sendmail availability) so it is actionable
      against the self-built layout.

## OIDC end-to-end coverage

- [ ] OIDC sign-in via Keycloak MUST work for Moodle's `auth/oidc`
      plugin against the realm provisioned by `web-app-keycloak`,
      with `email` claim verified and the persona auto-provisioned
      on first login.
- [ ] OIDC sign-out MUST log the user out of both Moodle and the
      Keycloak session (post-logout redirect honours
      `web-svc-logout`).
- [ ] The CLI configuration in
      [tasks/03_oidc.yml](../../roles/web-app-moodle/tasks/03_oidc.yml)
      MUST install, enable, and persist the `auth_oidc` plugin
      against the new code path; idempotent re-deploy MUST report
      `changed=0` on the second run.

## Profile-field mapping (Keycloak ↔ LDAP ↔ Moodle)

### Source-of-truth hierarchy

The role MUST enforce the following layered contract:

1. **Persistence / canonical store**: the **LDAP server** is the
   sole canonical store for every user-profile attribute listed
   in the [mapping table](#mapping-table). Every other component
   in the system reads from LDAP (directly or transitively) and
   never holds an authoritative copy that can drift from it.
2. **Definition of attribute correspondence (the SPOT)**: the
   **Keycloak LDAP user-federation mapper** is the single source
   of truth for "which LDAP attribute backs which Keycloak user-
   profile attribute". All other consumers MUST derive their
   field-name pairing from this mapper:
   - `auth_ldap` in Moodle MUST bind each Moodle column to the
     **same** LDAP attribute name that the Keycloak federation
     mapper uses for the equivalent Keycloak attribute.
   - The Keycloak OIDC client mappers for the Moodle RP MUST
     emit each claim from the **same** Keycloak attribute that
     the federation mapper feeds from LDAP.
   The
   [mapping table](#mapping-table) in this document MUST stay in
   sync with the Keycloak federation mapper definition; the
   table is the documented expression of the same SPOT.
3. **Edit surface**: end-user edits MUST happen exclusively via
   the **Keycloak Account Console** (or its admin equivalent for
   admin-managed attributes). Moodle MUST NOT expose editable
   profile fields for any attribute backed by LDAP; the role
   MUST lock the corresponding Moodle columns
   (`auth_ldap.config.field_lock_<col>=locked`) so edits made
   inside Moodle cannot diverge from LDAP.
4. **Propagation**: a Keycloak Account Console edit MUST flow
   into LDAP through the WRITABLE federation provider, then back
   into Moodle either via the next `auth_ldap` sync cycle (cron-
   driven, both variants) or via the next OIDC token mint
   (per-login refresh, variant 0 only).

This hierarchy means: Moodle is read-only for LDAP-backed
attributes, the Account Console is the only write surface, and
the Keycloak federation mapper is the configuration document
that everything else MUST match.

### Mapping table

Goal: every Moodle user-profile field that the standard
`mdl_user` table or a Moodle custom profile field can hold MUST
flow from the LDAP canonical store transparently into Moodle —
through Keycloak's federation mapper for the OIDC path, and
through Moodle's `auth_ldap` field-mapping for the LDAP-sync
path — both bound to the **same** LDAP attribute names.

The mapped surface MUST cover at minimum the following Moodle
fields, all of which are exposed as configurable claim mappings
by `auth_oidc` ("Plugins → Authentication → OIDC → Field
mapping"):

| Moodle field          | OIDC claim                      | LDAP attribute (cn=schema)    |
| --------------------- | ------------------------------- | ----------------------------- |
| `username`            | `preferred_username`            | `uid`                         |
| `firstname`           | `given_name`                    | `givenName`                   |
| `lastname`            | `family_name`                   | `sn`                          |
| `middlename`          | `middle_name`                   | `initials`                    |
| `alternatename`       | `nickname`                      | `displayName`                 |
| `firstnamephonetic`   | custom claim `name_phonetic_given`  | `infinitoNamePhoneticGiven` (custom)  |
| `lastnamephonetic`    | custom claim `name_phonetic_family` | `infinitoNamePhoneticFamily` (custom) |
| `email`               | `email`                         | `mail`                        |
| `phone1`              | `phone_number`                  | `telephoneNumber`             |
| `phone2`              | custom claim `phone_number_alt` | `mobile`                      |
| `address`             | `address.street_address`        | `street`                      |
| `city`                | `address.locality`              | `l`                           |
| `country`             | `address.country` (ISO-3166-1 alpha-2) | `c`                    |
| `institution`         | custom claim `institution`      | `o`                           |
| `department`          | custom claim `department`       | `ou`                          |
| `description` (bio)   | custom claim `description`      | `description`                 |
| `idnumber`            | custom claim `id_number`        | `employeeNumber`              |
| `url` (web page)      | `website`                       | `labeledURI`                  |
| `lang`                | `locale`                        | `preferredLanguage`           |
| `timezone`            | `zoneinfo`                      | `infinitoTimezone` (custom)   |

### Keycloak user profile (single source of truth)

- [ ] The realm provisioned by `web-app-keycloak` MUST enable the
      declarative user profile (`userProfileEnabled=true`).
- [ ] The user profile JSON MUST declare every attribute in the
      table above as a top-level attribute with appropriate
      `permissions.view = ['admin','user']` and
      `permissions.edit = ['admin','user']` (or admin-only for
      `idnumber`, `institution`, `department` if the tenant
      requires it; the role MUST default to user-editable and
      explicitly document any admin-only narrowing).
- [ ] Validation rules on each attribute MUST match Moodle's
      column constraints (e.g. ISO-3166-1 alpha-2 for `country`,
      RFC 5322 for `email`).

### LDAP schema extension (custom attributes)

The mapping table above introduces three attributes that are not
in the core LDAP schemas (`inetOrgPerson` /
`organizationalPerson` / `person` / `posixAccount`):
`infinitoNamePhoneticGiven`, `infinitoNamePhoneticFamily`, and
`infinitoTimezone`. These MUST be defined in a custom LDAP schema
shipped by the project's LDAP role rather than overloaded onto
existing attributes.

- [ ] A new schema file (e.g. `roles/svc-db-openldap/tasks/schemas/moodle.yml`)
      MUST register the three attribute types and an auxiliary
      object class `infinitoMoodleUser` that lists them under
      `MAY (...)`. The schema MUST follow the conventions of the
      existing
      [nextcloud schema](../../roles/svc-db-openldap/tasks/schemas/nextcloud.yml).
- [ ] The OID prefix MUST stay under the project's existing
      `1.3.6.1.4.1.99999.x` private-enterprise placeholder
      namespace (same root the Nextcloud schema uses); concrete
      OIDs MUST NOT collide with any existing assignment in the
      `roles/svc-db-openldap/tasks/schemas/` tree.
- [ ] Each attribute uses standard syntax:
  - `infinitoNamePhoneticGiven`, `infinitoNamePhoneticFamily`:
    DirectoryString, SINGLE-VALUE.
  - `infinitoTimezone`: IA5String, SINGLE-VALUE (IANA timezone
    name like `Europe/Berlin`).
- [ ] User entries created or migrated by the project MUST add
      the `infinitoMoodleUser` auxiliary class so the three
      attributes are storable on every user.
- [ ] On idempotent re-deploy of the LDAP role, the schema
      registration MUST report `changed=0` (i.e. the `cn=schema`
      entry is not re-pushed if it already matches).

### Keycloak ↔ LDAP user federation

- [ ] The Keycloak realm MUST configure an LDAP user-federation
      provider against the project LDAP server provisioned by the
      RBAC/LDAP roles (per
      [004-generic-rbac-ldap-auto-provisioning.md](004-generic-rbac-ldap-auto-provisioning.md)).
- [ ] An LDAP attribute mapper MUST exist for every row of the
      table above whose "LDAP attribute" column is populated. The
      mapper MUST be created by the role idempotently (e.g. via
      `kcadm.sh create user-federation/<id>/mappers/...`); a
      second deploy MUST report `changed=0`.
- [ ] The federation mode MUST be `WRITABLE` (or, if the LDAP
      server cannot accept writes from Keycloak, the role MUST
      pre-populate every mapped attribute on user creation via a
      separate path and document why `WRITABLE` was rejected).
- [ ] Edits made to a mapped attribute via the Keycloak
      Account Console (e.g. user updates `phone1`) MUST be
      written back to LDAP within the next sync interval (or
      synchronously, depending on the federation mode chosen).

### Custom-claim namespace

The four custom OIDC claims emitted by Keycloak for Moodle
(`name_phonetic_given`, `name_phonetic_family`,
`phone_number_alt`, `id_number`, `institution`, `department`,
`description`) MUST follow a flat snake_case naming convention
without a URN namespace. Rationale: `auth_oidc`'s field-mapping
UI lists every claim verbatim, so short names keep the operator-
facing config readable, and Keycloak emits them flat next to the
standard claims (`given_name`, `family_name`, …) which already
do not use URNs. The role MUST NOT introduce a project-specific
URN prefix for these claims.

### Keycloak OIDC client mapping (Moodle as RP) — variant 0 only

The Keycloak OIDC client representing Moodle MUST be provisioned
exclusively through the existing
[`web-app-keycloak`](../../roles/web-app-keycloak) auto-provisioning
path that consumes the per-app `services.oidc.enabled` flag
in [meta/services.yml](../../roles/web-app-moodle/meta/services.yml).
The Moodle role MUST NOT call `kcadm.sh create clients` itself.

- [ ] In **variant 0**, `services.oidc.enabled` is `true`, which
      triggers `web-app-keycloak`'s usual auto-provisioning of
      the client, the redirect URIs, and the role/scope
      mappings.
- [ ] In **variant 1**, `services.oidc.enabled` is `false`. The
      Moodle client MUST NOT be created in Keycloak in this
      variant (auto-provisioning skips it). Operators that
      switch between variants MUST be free to do so without
      orphan-client cleanup beyond what `web-app-keycloak`'s
      pruning already does.

- [ ] The Keycloak OIDC client representing Moodle MUST emit
      every claim listed in the table above on the access token
      and on the userinfo endpoint. Standard claims
      (`given_name`, `family_name`, `email`, `phone_number`,
      `address`, `website`, `locale`, `zoneinfo`,
      `preferred_username`, `middle_name`, `nickname`) MUST be
      provided by built-in OIDC scopes (`profile`, `email`,
      `phone`, `address`).
- [ ] Custom claims (`name_phonetic_given`,
      `name_phonetic_family`, `phone_number_alt`, `institution`,
      `department`, `description`, `id_number`) MUST be emitted
      via dedicated OIDC user-attribute mappers on the Moodle
      client. The mappers MUST be created idempotently by the
      role.

### Moodle `auth_oidc` field mapping (variant 0 only)

- [ ] The CLI configuration in
      [tasks/03_oidc.yml](../../roles/web-app-moodle/tasks/03_oidc.yml)
      MUST set the `auth_oidc` field-mapping table to consume
      every claim listed above and write it to the corresponding
      core `mdl_user` column.
- [ ] Every Moodle column in the
      [mapping table](#mapping-table) is part of core
      `mdl_user`, so the role MUST NOT create Moodle Custom
      Profile Fields for the canonical attribute set. If a
      future tenant requires an attribute that is NOT in core
      `mdl_user`, that attribute MUST be added in a follow-up
      requirement, not as a side-effect of this one.
- [ ] The mapping update mode for every field MUST be set to
      "Update on every login" (`oncreateupdate` ⇒ `2` /
      `oneveryloginupdate` ⇒ `2` per `auth_oidc` schema), so an
      attribute change in Keycloak is reflected at the user's
      next sign-in without manual re-provisioning.
- [ ] On idempotent re-deploy, the field-mapping MUST report
      `changed=0`.

### Moodle `auth_ldap` sync-only mode (both variants)

The `auth_ldap` plugin runs in **sync-only mode** in variant 0
(login is delegated to `auth_oidc`) and as the **primary login
plugin** in variant 1; the field-mapping configuration is
otherwise identical between the two variants and lives in a
single shared task file so neither variant drifts. Per the
[source-of-truth hierarchy](#source-of-truth-hierarchy), every
Moodle column MUST be configured `field_lock_<col>=locked`
(NOT `unlocked`) so Moodle remains read-only for LDAP-backed
attributes; the only write surface is the Keycloak Account
Console.

- [ ] A new task file `tasks/04_ldap_sync.yml` (or equivalent)
      MUST configure the `auth_ldap` plugin with:
  - LDAP server URL, bind DN, bind password, user contexts,
    user attribute (`uid` / `sAMAccountName` / per-tenant), and
    object class — all sourced from the same shared LDAP
    service definition that other apps consume, so the
    connection contract is not duplicated per role.
  - field-mapping for every Moodle column whose row in the
    [mapping table](#mapping-table) has a non-empty "LDAP
    attribute" cell.
  - `field_lock_<col>=locked` for every mapped column, so
    Moodle's profile UI MUST NOT allow edits to LDAP-backed
    attributes; the only write surface is the Keycloak Account
    Console (per the
    [source-of-truth hierarchy](#source-of-truth-hierarchy)).
  - the scheduled task `\auth_ldap\task\sync_task` enabled at
    an interval ≤ 15 minutes, so an attribute change in
    Keycloak/LDAP propagates to Moodle within one cron cycle
    even when the affected user does not log in again.
- [ ] `auth_ldap` user creation MUST be enabled
      (`auth_ldap.config.creators=*` for the relevant
      attribute-equivalence rule) so users that exist in LDAP
      but have never logged into Moodle are pre-provisioned by
      the sync task.
- [ ] `auth_ldap` user-removal action MUST be set to "Suspend"
      (NOT "Delete"), so a user removed from LDAP loses access
      but their Moodle history (forum posts, course
      enrolments) is preserved.
- [ ] In variant 0, the `auth_ldap` plugin MUST be hidden from
      the login page so users cannot bypass OIDC by entering
      LDAP credentials directly; the configuration that achieves
      this MUST be applied idempotently.
- [ ] On idempotent re-deploy, the `auth_ldap` configuration
      MUST report `changed=0`.

### End-to-end verification (Playwright)

The Playwright spec for `web-app-moodle` MUST cover both identity
variants and exercise three distinct propagation paths for every
mapped attribute: OIDC at login (variant 0), `auth_ldap` sync
without login (both variants), and direct LDAP-bind login
(variant 1).

#### Common (both variants)

- [ ] **Seed**: the spec MUST seed a known persona (default:
      `biber`) with every attribute listed in the
      [mapping table](#profile-field-mapping-keycloak-↔-ldap-↔-moodle)
      through the Keycloak Admin REST API (variant 0) or
      directly via LDAP modify (variant 1) before invoking the
      first Moodle login. Seed values MUST be fixture constants
      in the spec, NOT Faker-style randomness, so the assertion
      is deterministic.
- [ ] **LDAP-sync without login**: the spec MUST mutate biber's
      `phone1` server-side (variant 0: via Keycloak; variant 1:
      via direct LDAP modify), wait for the next `auth_ldap`
      sync cycle (or trigger it explicitly via
      `php /var/www/html/admin/cli/scheduled_task.php
      --execute='\auth_ldap\task\sync_task'` through `make exec`),
      and assert that biber's Moodle profile reflects the new
      `phone1` **without biber logging in again**. This proves
      the LDAP cron-sync path is wired correctly.
- [ ] The spec MUST be gated per
      [006-playwright-service-gated-tests.md](006-playwright-service-gated-tests.md).
      It MUST skip the variant-0-only cases cleanly (not fail)
      when the OIDC shared service is disabled via
      `SERVICES_DISABLED`, and skip the LDAP cases cleanly when
      the LDAP shared service is disabled.

#### Variant 0 — OIDC + LDAP sync (hybrid)

- [ ] After biber signs into Moodle via **Keycloak OIDC**, the
      spec MUST navigate to biber's Moodle profile page (or
      query Moodle's `/user/edit.php?id=<id>` rendered form) and
      assert that every field listed in the
      [mapping table](#profile-field-mapping-keycloak-↔-ldap-↔-moodle)
      renders the exact value seeded in Keycloak.
- [ ] **OIDC per-login refresh**: the spec MUST mutate biber's
      `phone2` in Keycloak, log biber out and back in, and
      assert the new value is reflected on biber's Moodle
      profile (validates the "Update on every login" semantic
      of `auth_oidc`).
- [ ] **LDAP read-through**: the spec MUST also assert that the
      mutated `phone2` is present in LDAP. The assertion path
      MUST be one of:
  1. an `ldapsearch` (or equivalent) query executed inside the
     runner via `make exec`, OR
  2. a Keycloak Account Console fetch that round-trips the
     attribute from LDAP (only acceptable if the federation
     provider is configured `READ_ONLY` and Keycloak's LDAP
     read-through proves provenance).
- [ ] The login page MUST NOT expose an LDAP-credential entry
      field; the spec MUST assert that only the SSO entry point
      is visible.
- [ ] **Read-only enforcement**: the spec MUST assert that
      Moodle's profile-edit form (`/user/edit.php?id=<biber-id>`)
      renders every LDAP-backed field as **disabled / read-only**
      (e.g. `<input … disabled>` or absence of the input
      altogether). Only the Account Console may edit; Moodle
      MUST refuse local edits.

#### Variant 1 — LDAP-only

- [ ] biber MUST sign into Moodle by submitting his LDAP `uid`
      and password directly to Moodle's login form. The spec
      MUST drive that login form (no OIDC redirect, no
      Keycloak round-trip).
- [ ] After login, the spec MUST navigate to biber's Moodle
      profile page and assert that every field listed in the
      [mapping table](#profile-field-mapping-keycloak-↔-ldap-↔-moodle)
      whose "LDAP attribute" cell is non-empty renders the
      value seeded directly in LDAP.
- [ ] The spec MUST mutate biber's `phone1` directly in LDAP
      (via `make exec` and `ldapmodify` against the project
      LDAP service), wait for the next `auth_ldap` sync cycle
      (or trigger it explicitly), and assert the new value
      appears on biber's Moodle profile **without biber
      logging in again**.
- [ ] The Moodle login page MUST NOT show an OIDC entry button
      in this variant; the spec MUST assert that only the
      `username` + `password` form is rendered.

## Playwright coverage

- [ ] `roles/web-app-moodle/files/playwright.spec.js` is created (or
      replaces any existing stub) and follows
      [006-playwright-service-gated-tests.md](006-playwright-service-gated-tests.md):
      every shared-service-dependent test MUST gate on the matching
      env flag.
- [ ] The spec MUST cover at minimum:
  1. **Baseline reachability**: `GET /` returns < 400, response
     carries the canonical domain from
     `lookup('domain', application_id)`.
  2. **CSP**: response headers include the role's CSP, no inline-
     script violations during landing.
  3. **administrator OIDC login**: dashboard → Moodle login button →
     Keycloak SSO with `ADMIN_USERNAME` / `ADMIN_PASSWORD` →
     authenticated Moodle UI. Logout returns to dashboard with
     no Keycloak session left behind.
  4. **biber OIDC login**: same as (3) for `BIBER_USERNAME` /
     `BIBER_PASSWORD`.
  5. **administrator + biber together**: admin and biber both sign
     in via OIDC, biber's persona is auto-provisioned on first
     login (no manual user creation required), and admin can see
     biber listed under Site administration → Users → Browse list
     of users.
- [ ] Spec credentials MUST be sourced exclusively from the
      Playwright env injection (`ADMIN_USERNAME`, `ADMIN_PASSWORD`,
      `BIBER_USERNAME`, `BIBER_PASSWORD`); no hard-coded
      credentials in the spec file.
- [ ] The spec MUST install `installCspViolationObserver(page)` in
      `test.beforeEach` per the existing project convention.
- [ ] The spec MUST run green via the project's standard
      Playwright entry point in CI (`test-e2e-playwright` role).

## CI matrix

- [ ] Both variants MUST run in the project's CI matrix-deploy
      job (`test-deploy-server`) so a regression on either
      identity-integration shape is caught before merge. The
      doubled CI cost (≈ 2× the single-variant baseline for this
      role) is accepted as the cost of validating both supported
      tenants.
- [ ] If CI capacity becomes a hard constraint in a follow-up,
      the role MAY be split per a future requirement; this
      requirement does NOT permit dropping a variant from CI as
      a unilateral cost-saving move.

## Iteration procedure

The implementing agent MUST iterate on this role per
[role.md](../agents/action/iteration/role.md), with the matrix-
variant guidance from [variants.md](../contributing/design/variants.md)
applied because the role ships two identity-integration variants.

- [ ] Propose `SERVICES_DISABLED="matomo,email"` once at the start
      and persist that decision for every deploy in the iteration.
- [ ] First deploy MUST be a **FULL-matrix** baseline:
      `make deploy-fresh-purged-apps APPS=web-app-moodle
      FULL_CYCLE=true`. This iterates rounds 0 and 1 against
      both variants in order; the inter-round purge runs because
      the variant changes between them.
- [ ] Edit-fix-redeploy iterations MUST be done **per variant**.
      The agent MUST pin `VARIANT=0` (or `VARIANT=1`) on every
      command for the variant it is currently iterating, and
      MUST state the choice explicitly before the first command:
  - `VARIANT=<idx> make deploy-reuse-kept-apps APPS=web-app-moodle`
    is the default reuse-deploy.
  - `VARIANT=<idx> make deploy-reuse-purged-apps APPS=web-app-moodle`
    MAY be used once when reuse-kept reproduces a failure and
    entity-state involvement is suspected, then the agent MUST
    return to reuse-kept.
- [ ] When debugging cross-variant interactions (e.g. variant 1
      breaks because variant-0 LDAP/OIDC state was not purged),
      the agent MUST first reproduce with the FULL matrix
      (omit `VARIANT=`), then pin to the failing variant for
      the focused fix loop, and re-run the FULL matrix once the
      fix is believed complete.
- [ ] `make test` MUST pass before every deploy.
- [ ] When both variants' deploys are green, the agent MUST run
      [Playwright Spec Loop](../agents/action/iteration/playwright.md)
      against `roles/web-app-moodle/files/playwright.spec.js`
      pinned to each variant in turn, and confirm every spec
      scenario passes on the local stack for both variants.
- [ ] All inspection (live logs, browser, `make exec`) MUST happen
      before each redeploy, per [role.md](../agents/action/iteration/role.md).

## Autonomy & commit policy

- [ ] The agent MUST work the full requirement to completion
      without intermediate operator intervention. Questions for the
      operator are deferred until **after** every Acceptance
      Criterion above is checked off.
- [ ] The agent MUST NOT create any git commit during
      implementation. No partial commits, no checkpoint commits.
- [ ] When all Acceptance Criteria are checked, `make test` is
      green, the role iteration loop reports a clean reuse-deploy,
      and Playwright is green, the agent lands the entire change
      set as a **single** commit on
      `feature/moodle-self-built` and then instructs the operator
      to run `git-sign-push` outside the sandbox per
      [CLAUDE.md](../../CLAUDE.md).
- [ ] Only after the single commit is in place, the agent MAY
      surface any open questions or design follow-ups for the
      operator (collected in batch, not asked mid-iteration).

## Prerequisites

Before starting any implementation work, the agent MUST read
[AGENTS.md](../../AGENTS.md) and follow all instructions in it. The
existing `bitnamilegacy/moodle`-based role is the structural
reference for the shared-service wiring; deviating from those
conventions requires explicit justification.
