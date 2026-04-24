# Remotes 🌐

This repository uses a fork-based workflow. Contributors SHOULD NOT configure the remote layout by hand. Remote setup and signed pushes are handled by [git-maintainer-tools](https://github.com/kevinveenbirkenbach/git-maintainer-tools), declared as a dev dependency in [pyproject.toml](../../../../pyproject.toml).

## Layout 🗺️

| Remote | URL | Role |
|---|---|---|
| `origin` | `git@github.com:infinito-nexus/core.git` | Canonical / upstream. `main` tracks `origin/main`. Pull target. |
| `fork` | `git@github.com:<user>/infinito-nexus-core.git` | Personal fork. Push target for every branch. |

The tool enforces `remote.pushDefault = fork` so every push (and every new-branch push via `git-sign-push`) lands on the fork, not on the canonical repo, while `main` keeps pulling from canonical.

## Tools 🧰

| CLI | Purpose |
|---|---|
| `git-setup-remotes` | Idempotently configures `origin`, `fork`, main-tracking, and `remote.pushDefault` on a clone. |
| `git-sign-push` | GPG-signs every unpushed commit on the current branch and pushes to the fork (or the branch's upstream if set). Resolves the target from `remote.pushDefault`, falling back to `origin`. |

Both CLIs refuse to run inside the Claude sandbox because `.git/config` writes and `~/.gnupg` access are blocked there per the Git Safety Protocol in [settings.md](../../tools/agents/claude/settings.md).

## Install 📦

```bash
make install-python-dev
```

This pulls in [git-maintainer-tools](https://github.com/kevinveenbirkenbach/git-maintainer-tools) through the project's `dev` extras and puts `git-setup-remotes` and `git-sign-push` on `$PATH`.

## Usage 🚀

- One-time setup (run once after cloning, outside the Claude sandbox): `git-setup-remotes --canonical git@github.com:infinito-nexus/core.git`. See the tool's [README](https://github.com/kevinveenbirkenbach/git-maintainer-tools#readme) for all flags, the `FORK_URL` environment variable, and the clone-from-canonical case.
- Shipping a branch: commit per [commit.md](commit.md), then run `git-sign-push` outside the sandbox. Open the pull request against `origin/main` per [pull-request.md](pull-request.md).
