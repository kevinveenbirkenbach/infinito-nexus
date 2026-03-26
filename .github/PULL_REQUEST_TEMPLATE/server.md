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

## Local Validation

Describe how the change was validated locally.

* Deployment target and distro:
* Playwright test run:
* Login flow tested:
* Logout flow tested:
* Screenshot attached:

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
For the repository-wide reviewer checklist, see https://s.infinito.nexus/reviewguide.

* Highest-risk files, roles, or flows:
* Migration, rollback, or security-sensitive concerns:
* Specific feedback requested from reviewers:

---

## Definition of Done (DoD)

### Workflow

* [ ] Contributions follow the [collaboration workflow](https://hub.infinito.nexus/t/working-with-folks-in-infinito-nexus/436)

### Code Quality

* [ ] Code follows repository conventions
* [ ] Code and comments are written in English

### Functionality

* [ ] Change works as expected in a local deployment
* [ ] Original upstream Docker image was used for testing where practical

### Testing

* [ ] Changes tested locally
* [ ] CI pipeline passes
* [ ] Playwright test added or updated for the affected `web-*` flow
* [ ] Playwright test verifies login and logout
* [ ] Unit test added for touched `*.py` files
* [ ] Integration test added for touched `*.py` files

### Documentation

* [ ] Relevant `README.md` files and docs updated
* [ ] Link this PR to the work item in https://project.infinito.nexus/ and back
* [ ] Work item in https://project.infinito.nexus/ updated
* [ ] Screenshot of the running application from the local deployment attached when the change is user-visible

---

## Additional Notes

Add any reviewer context that is useful for deployment, rollback, or follow-up work.
