## Summary

Briefly describe the system-level change.

Examples:

* Add a new `sys-*`, `svc-*`, `dev-*`, `drv-*`, `pkgmgr`, `update-*`, or `user-*` capability
* Fix broken shared infrastructure, package, service, or automation behavior
* Extend a shared service, package, timer, or maintenance workflow
* Introduce a new infrastructure, shared abstraction, or automation building block

---

## Template Type

Select the primary intent of this PR:

* [ ] **Feature** - Adds or extends shared system functionality
* [ ] **Fix** - Repairs broken or incorrect shared system behavior

---

## Affected Components

List the impacted roles and shared components.

* Primary role(s) or module(s):
* Related services, timers, packages, inventories, or workflows:
* Distro(s) tested:

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

* What capability was introduced?
* How does this integrate with the existing stack?
* Were variables, defaults, and shared logic kept DRY?
* Are there architecture, migration, or compatibility implications?
* Which alternatives were considered?

---

## Local Validation

Describe how the change was validated locally.

* Fresh deploy or targeted rerun tested:
* Idempotency verified:
* Service health, timers, or package behavior verified:
* Cross-distro notes:

---

## Security Impact

Indicate whether this change has security implications.

* [ ] No relevant security impact
* [ ] Security impact present

If security impact is present, explain:

* Affected auth, TLS, permissions, secrets, services, or exposed surfaces:
* Risk reduction, new exposure, migration, or compatibility considerations:
* Security-specific validation performed:

---

## Review Focus

Help reviewers focus on the riskiest parts of this PR.
For the repository-wide reviewer checklist, see https://s.infinito.nexus/reviewguide.

* Highest-risk files, roles, or flows:
* Idempotency, compatibility, or rollout concerns:
* Specific feedback requested from reviewers:

---

## Definition of Done (DoD)

### Workflow

* [ ] Contributions follow the [collaboration workflow](https://hub.infinito.nexus/t/working-with-folks-in-infinito-nexus/436)

### Code Quality

* [ ] Code follows repository conventions
* [ ] Code and comments are written in English
* [ ] Shared logic and variables were kept DRY where practical

### Functionality

* [ ] Change works as expected in the tested environment
* [ ] Idempotency and service behavior were verified where applicable

### Testing

* [ ] Changes tested locally
* [ ] CI pipeline passes
* [ ] Unit test added for touched `*.py` files
* [ ] Integration test added for touched `*.py` files

### Documentation

* [ ] Relevant `README.md` files and docs updated
* [ ] Link this PR to the work item in https://project.infinito.nexus/ and back
* [ ] Work item in https://project.infinito.nexus/ updated

---

## Additional Notes

Add any reviewer context for rollout, compatibility, or operational follow-up.
