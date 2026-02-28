# Working with Folks in Infinito.Nexus

Infinito.Nexus follows a strict and scalable contribution model designed for stability, quality assurance, and CI/CD efficiency.
All development must take place in **Folks (Forks)** — never directly in the main repository.

This document explains the workflow and the reasoning behind it.

---

## 1. Create a Folk (Fork) – Never Work on Main

Before starting any change:

1. Fork the official Infinito.Nexus repository
   👉 [https://github.com/kevinveenbirkenbach/infinito-nexus](https://github.com/kevinveenbirkenbach/infinito-nexus)

2. Clone your personal fork.

3. Create a feature branch in your fork.

4. Implement your changes there.

All development — features, bug fixes, refactoring, documentation, or experiments — must happen inside your forked repository.

### Why?

* Keeps `main` stable at all times
* Prevents broken pipelines
* Enables isolated CI testing
* Allows experimentation without risk

The `main` branch is considered production-grade and must remain clean and green.

---

## 2. Work Inside Your Folk

Inside your fork:

* Follow the established repository structure.
* Respect the canonical role templates and patterns.
* Follow naming conventions and CI/CD integration standards.
* Keep commits small and meaningful.
* Ensure reproducibility.

Before even thinking about a Pull Request:

✔ Run all local tests
✔ Validate linting
✔ Ensure formatting compliance
✔ Confirm CI passes in your fork

---

## 3. CI/CD Must Pass in the Fork First

This is critical.

**All CI/CD pipelines in your fork must pass before creating a Pull Request.**

Why is this mandatory?

The main repository’s CI/CD runners are shared and limited resources.
If contributors push untested or failing changes directly into PRs, it:

* Overloads the main action runners
* Delays other contributors
* Consumes unnecessary compute resources
* Reduces overall system reliability

### Therefore:

> ❗ If CI fails in your fork, fix it there — do not rely on the main repository to test it for you.

Your fork is your responsibility.
The main repository is not a testing playground.

---

## 4. Pull Request Requirements

Only create a Pull Request when:

* Your fork’s CI pipeline is fully green
* The branch is rebased on current `main`
* Changes are documented
* Commit history is clean

A Pull Request should:

* Be small and focused
* Explain the purpose clearly
* Reference related issues if applicable
* Follow semantic structure

---

## 5. Why This Model Matters

Infinito.Nexus is designed to scale.

Without a strict fork-based workflow:

* CI/CD becomes unstable
* Review overhead increases
* Regression risk rises
* The project velocity drops

By enforcing:

* Fork-first development
* Green CI in fork
* Clean PR submission

we ensure:

* Stable `main`
* Efficient resource usage
* High-quality merges
* Predictable delivery cycles

---

## 6. Summary

**Golden Rule:**

> Work in your Folk.
> Pass CI in your Folk.
> Then open a Pull Request.

No direct commits to main.
No CI failures in PR.
No shortcuts.

This keeps Infinito.Nexus robust, scalable, and sustainable.
