# Remotes 🌐

This repository uses a fork-based workflow. Contributors MUST NOT configure the remote layout by hand. Remote setup and signed pushes are handled by [git-maintainer-tools](https://github.com/kevinveenbirkenbach/git-maintainer-tools), declared as a dev dependency in [pyproject.toml](../../../../pyproject.toml).

## Layout 🗺️

| Remote | URL | Role |
|---|---|---|
| `origin` | `git@github.com:infinito-nexus/core.git` | Canonical upstream. Pull target for all branches. Push target for `main`. |
| `fork` | `git@github.com:<user>/infinito-nexus-core.git` | Personal fork. Push target for every branch except `main`. |

## Push Routing 🛤️

`git-setup-remotes` writes three git-config keys that together route pushes:

| Key | Value | Effect |
|---|---|---|
| `remote.pushDefault` | `fork` | Default push target for every branch. |
| `push.default` | `current` | `git push` targets the same-named branch on the remote. |
| `branch.main.pushRemote` | `origin` | Overrides the default for `main` so canonical-branch pushes go upstream and never land on the personal fork, whose branch-protection rules can diverge from canonical. |

`main` keeps tracking `origin/main` for `git pull`, independent of the push override.

## Tools 🧰

| CLI | Purpose |
|---|---|
| `git-setup-remotes` | Idempotently configures `origin`, `fork`, `main`-tracking, and the push-routing keys above. |
| `git-sign-push` | GPG-signs every unpushed commit on the current branch and pushes. The target resolves from the branch's upstream and honours `branch.<name>.pushRemote`. Branches without an upstream fall back to `remote.pushDefault`, then `origin`. |

Both CLIs MUST run outside the Claude sandbox, because `.git/config` writes and `~/.gnupg` access are blocked there per the Git Safety Protocol in [settings.md](../../tools/agents/claude/settings.md).

## Install 📦

```bash
make install-python-dev
```

This pulls in [git-maintainer-tools](https://github.com/kevinveenbirkenbach/git-maintainer-tools) through the project's `dev` extras and puts `git-setup-remotes` and `git-sign-push` on `$PATH`.

## Usage 🚀

- One-time setup (run once after cloning, outside the Claude sandbox): `git-setup-remotes --canonical git@github.com:infinito-nexus/core.git`. See the tool's [README](https://github.com/kevinveenbirkenbach/git-maintainer-tools#readme) for all flags, the `FORK_URL` environment variable, and the clone-from-canonical case.
- Shipping a branch: commit per [commit.md](commit.md), then run `git-sign-push` outside the sandbox. Open the pull request against `origin/main` per [pull-request.md](pull-request.md).
