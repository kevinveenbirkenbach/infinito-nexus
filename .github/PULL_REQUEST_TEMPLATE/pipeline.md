## Summary

Briefly describe the CI/CD or pipeline change and the expected effect.

Examples:

* Add a new workflow or reusable workflow
* Fix flaky CI, release, or image automation behavior
* Improve workflow permissions, observability, or execution flow

---

## Template Type

Select the primary intent of this PR:

* [ ] **Feature** - Adds or extends CI/CD functionality
* [ ] **Fix** - Repairs broken or incorrect CI/CD behavior

---

## Affected Components

List the impacted workflows and related automation.

* Workflow file(s):
* Related scripts, actions, jobs, or images:
* Fork, PR, release, or scheduled paths affected:

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

* What pipeline problem or capability does this address?
* How do triggers, permissions, concurrency, or artifacts behave after this change?
* Are fork, secret, or release paths affected?
* Which alternatives were considered?

---

## Validation

Describe how the pipeline change was validated.

* Local or targeted script validation performed:
* Workflow run in fork or equivalent validation:
* Relevant logs or run links attached:
* Failure-path or retry behavior checked:

---

## Security Impact

Indicate whether this change has security implications.

* [ ] No relevant security impact
* [ ] Security impact present

If security impact is present, explain:

* Affected permissions, secrets, tokens, artifacts, or release surfaces:
* Risk reduction, new exposure, fork-safety, or compatibility considerations:
* Security-specific validation performed:

---

## Review Focus

Help reviewers focus on the riskiest parts of this PR.
For the repository-wide reviewer checklist, see https://s.infinito.nexus/reviewguide.

* Highest-risk workflows, jobs, or scripts:
* Permissions, fork-safety, release, or security-sensitive concerns:
* Specific feedback requested from reviewers:

---

## Definition of Done (DoD)

### Workflow

* [ ] Contributions follow the [collaboration workflow](https://hub.infinito.nexus/t/working-with-folks-in-infinito-nexus/436)

### Code Quality

* [ ] Code follows repository conventions
* [ ] Code and comments are written in English

### Functionality

* [ ] Change works as expected in the tested CI/CD path
* [ ] Trigger behavior, permissions, and failure handling were verified where applicable

### Testing

* [ ] Changes tested locally where practical
* [ ] CI pipeline passes
* [ ] Relevant workflow or script paths were validated
* [ ] Unit test added for touched `*.py` files
* [ ] Integration test added for touched `*.py` files

### Documentation

* [ ] Relevant workflow docs, `README.md` files, or runbook notes updated
* [ ] Link this PR to the work item in https://project.infinito.nexus/ and back
* [ ] Work item in https://project.infinito.nexus/ updated

---

## Additional Notes

Add any reviewer context for rollout, fork behavior, release impact, or follow-up work.
