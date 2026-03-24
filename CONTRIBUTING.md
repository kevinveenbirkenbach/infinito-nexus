# 🚀 Contributing to Infinito.Nexus

Thank you for your interest in contributing to **Infinito.Nexus**! 🙌

We genuinely appreciate every contribution — whether it's code, documentation, testing, bug reports, or ideas.
Your involvement helps make Infinito.Nexus more stable, scalable, and powerful.

Before getting started, please read this document carefully.
Infinito.Nexus follows a **strict fork-first contribution model** to ensure long-term stability and CI/CD efficiency.

This workflow is mandatory for all contributors. 💡

---

# 🔐 Our Core Rule: Fork First. Always.

All development must happen in **Folks (Forks)** — never directly in the main repository.

The `main` branch is production-grade.
It must remain stable, clean, and green at all times. ✅

---

## 🧭 Step 1 — Create Your Folk (Fork)

Before making any change:

1. Fork the official repository
   👉 [https://github.com/infinito-nexus/core](https://github.com/infinito-nexus/core)

2. Clone your fork locally.

3. Create a feature branch inside your fork.

4. Implement your changes there.

This applies to everything:

* ✨ New features
* 🐛 Bug fixes
* ♻ Refactoring
* 📚 Documentation
* 🧪 Experiments

No direct commits to `main`. No exceptions.

---

## 🤔 Why This Model?

This strict model ensures:

* 🟢 `main` always stays stable
* ⚙️ CI pipelines remain efficient
* 🧪 Experiments are isolated
* 💻 Shared runners are protected
* 📈 The project scales sustainably

Your fork is your workspace.
The main repository is not a testing playground.

---

# 🛠 Working Inside Your Folk

Once inside your fork:

* Follow the established repository structure.
* Respect canonical role templates and patterns.
* Follow naming conventions.
* Keep commits small and meaningful.
* Ensure changes are reproducible.

Before opening a Pull Request:

✔ Run all local tests
✔ Validate linting
✔ Ensure formatting compliance
✔ Confirm CI passes in your fork

---

# 🧪 Required Local Checks

All checks are run via `make` from the repository root.

---

## 🎨 Formatting

```bash
make format
```

---

## 🧹 Linting & Tests (CI-like via Docker)

Start the CI stack:

```bash
make up
```

Run checks:

```bash
make test-lint
make test-unit
make test-integration
```

Run everything:

```bash
make test
```

Optional teardown:

```bash
make down
```

---

## 📦 Ansible Syntax Check

```bash
make lint-ansible
```

---

## 🌍 Local Deployment Testing

For full end-to-end deployment validation using the local Docker-based development environment, follow the official setup guide on the Hub:

👉 [https://hub.infinito.nexus/t/local-deploy-test-scripts/435](https://hub.infinito.nexus/t/local-deploy-test-scripts/435)

This guide explains how to:

* Run Infinito.Nexus locally
* Deploy apps under `*.infinito.example`
* Use the local development test scripts
* Perform smoke tests

Some commands are destructive — read carefully before running them. ⚠️

---

# 🟢 CI Must Pass in Your Fork First

This is critical.

**All CI/CD pipelines must pass in your fork before opening a Pull Request.**

If CI fails in your fork:

> Fix it there. Do not rely on the main repository to test it for you.

Why?

* 🖥 Main runners are shared and limited
* ❌ Broken PRs waste compute resources
* ⏳ They delay other contributors
* 📉 They reduce reliability

Your fork = your responsibility.

---

# 📬 Pull Request Requirements

Only open a Pull Request when:

* ✅ CI in your fork is fully green
* 🔄 Your branch is rebased on current `main`
* 📚 Changes are documented
* 🧹 Commit history is clean
* 🧪 Tests pass locally

A good Pull Request:

* Is small and focused
* Clearly explains its purpose
* References related issues
* Follows semantic structure

---

# 💬 Community & Discussion

For questions, development discussions, architecture topics, and Q&A, please use the official Hub:

👉 [https://hub.infinito.nexus/](https://hub.infinito.nexus/)

The Hub is the central place for:

* ❓ Q&A
* 🧠 Architecture discussions
* 🛠 Development topics
* 📣 Announcements
* 🧪 Testing feedback

We encourage using the Hub instead of GitHub issues for general discussions.

---

# 🐛 Reporting Issues

Bug reports and actionable feature requests should be opened via:

👉 [https://s.infinito.nexus/issues](https://s.infinito.nexus/issues)

Please include:

* Clear description
* Steps to reproduce
* Environment details
* Relevant logs

---

# 🤝 Code of Conduct

All contributors must follow:

`CODE_OF_CONDUCT.md`

Respectful, professional collaboration is expected at all times.

---

# 🌱 Why This Matters

Infinito.Nexus is designed to scale.

Without strict fork-first development:

* CI/CD becomes unstable
* Review overhead increases
* Regression risk rises
* Development velocity drops

By enforcing:

* Fork-first development
* Green CI in forks
* Clean Pull Requests

we ensure:

* 🟢 Stable `main`
* ⚡ Efficient CI usage
* 🧩 High-quality merges
* 📈 Sustainable growth

---

# 🏁 Golden Rule

> Work in your Folk.
> Pass CI in your Folk.
> Then open a Pull Request.

No direct commits to `main`.
No CI failures in PR.
No shortcuts.

Thank you for helping make **Infinito.Nexus** robust, scalable, and future-proof. 💙
