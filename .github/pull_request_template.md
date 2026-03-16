## Summary

Briefly describe the purpose of this pull request.

Example:

* Add new role for application X
* Fix configuration issue in role Y
* Improve container startup logic

---

## Change Type

Select the semantic version impact of this change:

* [ ] **Major** – Breaking change (incompatible configuration or behaviour)
* [ ] **Minor** – New feature or new role (backwards compatible)
* [ ] **Patch** – Bugfix or internal improvement

### Breaking Changes

If this PR introduces breaking changes, describe them here.

Example:

* renamed variable `ldap_user_dn` → `ldap_bind_dn`
* removed deprecated configuration option

---

## Description of Changes

Explain what was changed and why.

Key points:

* What problem does this solve?
* Why was this implementation chosen?
* Are there alternative approaches?

---

## Local Testing

For **new roles**, please provide evidence that the application was successfully deployed and tested locally.

* Follow the local test environment [setup guide](https://hub.infinito.nexus/t/local-test-environment-deploy/435)

* [ ] Attach a **screenshot of the running application** from the local deployment.

---

## Definition of Done (DoD)

Please ensure all items are completed before requesting review.

### Code Quality

* [ ] Code follows repository conventions
* [ ] Code and comments are written in English

### Functionality

* [ ] Feature works as expected

### Testing

* [ ] Changes tested locally
* [ ] CI pipeline passes
* [ ] E2E test introduced for web-* roles
* [ ] Unit test integrated for *.py files
* [ ] Integration test integrated for *.py files

### Documentation

* [ ] README.md's and other *.md updated

---

## Collaboration Guidelines

All contributions should follow the [collaboration workflow](https://hub.infinito.nexus/t/working-with-folks-in-infinito-nexus/436)

This includes guidelines for:

* communication
* contribution workflow
* review expectations
* repository standards

---

## Impacted Areas

Select affected components.

* [ ] Role implementation
* [ ] Configuration variables
* [ ] Documentation
* [ ] CI/CD
* [ ] Security

---

## Checklist for Reviewer

Reviewer should verify:

* [ ] Code is understandable
* [ ] Changes follow project guidelines
* [ ] Documentation is adequate
* [ ] No obvious security issues

---

## Additional Notes

Add anything reviewers should know.
