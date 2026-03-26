## Summary

Briefly describe the `web-*` change and the expected user-facing outcome.

Examples:

* Add a new `web-app-*` role
* Fix a broken login, bootstrap, or integration flow in an existing `web-*` role
* Introduce SSO or mail integration for an existing `web-*` role
* Extend bootstrap or deployment behavior for a server-facing application

---

## Template Type

Select the primary intent of this PR:

* [ ] **Feature** - Adds or extends server functionality
* [ ] **Fix** - Repairs broken or incorrect server behavior

---

## Affected Roles and Services

List the impacted roles and related services.

* Primary `web-*` role(s):
* Related `web-svc-*`, `sys-front-*`, `svc-db-*`, auth, mail, proxy, or storage role(s):

---

## Change Type

Select the semantic version impact of this change:

* [ ] **Major** - Breaking change
* [ ] **Minor** - New backwards-compatible feature
* [ ] **Patch** - Small improvement or compatible adjustment

---

## Change Details

Explain what changed and why.

Key points:

* What problem does this solve?
* Which upstream image or service version was used or changed?
* How do login, logout, proxying, storage, or mail integration behave after this change?
* Which alternatives were considered?

---

## File Checklist

Check the relevant rows and explain intentional omissions in `Additional Notes`.

| Check | Item | When to include | Purpose |
|---|---|---|---|
| [ ] | `README.md` | Usually | Documents role-specific usage, setup notes, and contributor context. |
| [ ] | `meta/main.yml` | Usually | Declares role metadata and dependencies. |
| [ ] | `vars/main.yml` | Usually | Defines the shared fixed role variables as the main source of truth. |
| [ ] | `config/main.yml` | Usually | Defines the configurable app-facing settings for the role. |
| [ ] | `schema/main.yml` | When schema validation is used | Describes and validates the supported configuration surface. |
| [ ] | `tasks/main.yml` | Usually | Acts as the role entry point and includes the main task flow. |
| [ ] | `templates/compose.yml.j2` | For containerized app roles | Defines the service, volume, environment, port, and network wiring. |
| [ ] | `templates/env.j2` | When the app uses environment files | Renders the app environment configuration. |
| [ ] | `users/main.yml` | When the role bootstraps users or identities | Defines user bootstrap or role-specific user management data. |
| [ ] | `files/Dockerfile` | When a custom image is required | Provides a custom image build path. Prefer this over `Dockerfile.j2`. |
| [ ] | `templates/playwright.env.j2` | When Playwright coverage is included | Configures the Playwright test environment. |
| [ ] | `files/playwright.spec.js` | When Playwright coverage is included | Defines the Playwright login and logout test flow. |

### Registered

| Check | Item | When to include | Purpose |
|---|---|---|---|
| [ ] | Port defined in `group_vars/all/11_ports.yml` | When the app exposes a service | Confirms that the app port is defined consistently in the central port mapping. |
| [ ] | Network defined in `group_vars/all/10_networks.yml` | When the app communicates over container networks | Confirms that the required network wiring is defined consistently in the central network mapping. |

---

## Local Validation

Describe how the change was validated locally.

* [ ] Deployment target and distro documented
* [ ] Playwright test run documented
* [ ] Login flow tested
* [ ] Logout flow tested
* [ ] Screenshot attached when the change is user-visible

---

## Security Impact

Indicate whether this change has security implications.

* [ ] No relevant security impact
* [ ] Security impact present

If security impact is present, explain:

* Affected auth, TLS, permissions, secrets, headers, or exposed surfaces:
* Risk reduction, new exposure, or compatibility considerations:
* Security-specific validation performed:

---

## Review Focus

Help reviewers focus on the riskiest parts of this PR.
For repository-wide contribution and review expectations, see [CONTRIBUTING.md](../../CONTRIBUTING.md).

* Highest-risk files, roles, or flows:
* Migration, rollback, or security-sensitive concerns:
* Specific feedback requested from reviewers:

---

## Definition of Done (DoD)

* [ ] The implementation follows the Definition of Done, and the contribution guidelines in [CONTRIBUTING.md](../../CONTRIBUTING.md) were considered and applied during implementation.

---

## Additional Notes

Add any reviewer context that is useful for deployment, rollback, or follow-up work.
