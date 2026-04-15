# Claude Code Settings 🤖

This page documents every permission entry in [`.claude/settings.json`](../../../../.claude/settings.json) and explains when it applies, why it is granted at that level, and what security implications it carries.
For general agent workflow rules, see [common.md](common.md).
For the Claude Code permission model reference, see [docs.anthropic.com](https://docs.anthropic.com/en/docs/claude-code/settings).

## Permission Model 🔐

Claude Code evaluates each tool call against three ordered lists:

| List | Behavior |
|---|---|
| `allow` | Executes automatically without prompting. |
| `ask` | Pauses and asks the operator for approval before executing. |
| `deny` | Rejects the call unconditionally, even if `allow` would otherwise match. |

`deny` takes precedence over `allow`. `settings.local.json` MAY extend project permissions locally but MUST NOT weaken `deny` rules defined here.

## Allow Permissions ✅

### File Tools ✏️

| Permission | When | Why | Security |
|---|---|---|---|
| `Read` | Every task that inspects a file. | Core IDE operation. The agent cannot understand code without it. | Scope is limited by `denyRead` in the sandbox section. Credential directories are never readable. |
| `Edit` | Every task that modifies an existing file. | Core IDE operation. Required for any code change. | Write scope is bounded by `allowWrite`. Changes outside `.` and `/tmp` are blocked. |
| `Write` | Every task that creates a new file. | Core IDE operation. Required for scaffolding and new file creation. | Same sandbox boundary as `Edit`. |

### Git Commands 🗃️

| Permission | When | Why | Security |
|---|---|---|---|
| `git status*` | Before any task to inspect the working tree. | Read-only state inspection. Required for every task that touches the repository. | No write side-effects. Safe to allow unconditionally. |
| `git log*` | Reviewing history, finding commits, checking recent changes. | Read-only history access. | No write side-effects. Safe to allow unconditionally. |
| `git diff*` | Comparing changes before staging or committing. | Read-only diff output. | No write side-effects. Safe to allow unconditionally. |
| `git add*` | Staging changes as part of a task before a commit is requested. | Prerequisite for committing. | Affects the index only, not the remote. Destructive intent requires `git commit` and `git push`, both in `ask`. |
| `git mv*` | Renaming or moving tracked files. | Required for rename and restructuring tasks. | Affects the index only. Reversible before committing. |
| `git rm*` | Removing tracked files as part of a task. | Required for delete tasks. | Affects the index only. Reversible before committing. |
| `git checkout*` | Switching branches or restoring individual files. | Standard branch-management operation. | Can discard local changes when used with a path argument. The `deny` rule for `git reset --hard` mitigates the broader discard risk. |
| `git branch*` | Creating, listing, or deleting local branches. | Required during feature and fix workflows. | Local only. Remote branches require `git push`, which is in `ask`. |
| `git fetch*` | Fetching remote state without merging. | Needed to compare local and remote state before taking action. | Read-only from the network perspective. Does not modify the working tree. |
| `git stash*` | Temporarily shelving uncommitted work before switching context. | Needed when the agent must change branches without losing in-progress edits. | Reversible. No data leaves the machine. |
| `git cherry-pick*` | Applying isolated commits from other branches. | Required for backport tasks. | Modifies the working tree and index. Operators SHOULD review the source commit before approving the task. |
| `git apply*` | Applying patch files to the working tree. | Required for patch-based workflows. | Modifies the working tree and index. Operators SHOULD review the patch source before approving the task. |
| `git -C*` | Running git commands in a sub-path of the repository. | Some scripts and make targets invoke git outside the current working directory. | Equivalent to the base git commands above. No additional privilege is granted. |

### GitHub CLI 🐙

| Permission | When | Why | Security |
|---|---|---|---|
| `gh run*` | Inspecting CI pipeline runs, viewing logs, or listing workflow run status. | Allows the agent to check whether a workflow passed without browser access. | Primarily read-only. Subcommands such as `gh run rerun` and `gh run cancel` are write operations covered by this wildcard. Operators SHOULD verify the subcommand when approving tasks. |

### Build and Scripts 🛠️

| Permission | When | Why | Security |
|---|---|---|---|
| `make*` | Running any target defined in the repository `Makefile`. | Make is the primary command surface covering install, test, lint, build, deploy, and cleanup. | The full wildcard is broad. The `Makefile` MUST NOT expose targets that run privileged or destructive operations without explicit guards. New make targets SHOULD be reviewed before merging. |
| `act*` | Running GitHub Actions workflows locally via Act. | Used by `make act-*` targets for local CI simulation. | Act pulls Docker images and executes workflow steps locally. Workflows MUST NOT contain untrusted third-party actions before running. |
| `bash -n*` | Syntax-checking shell scripts before executing them. | `bash -n` is a dry-run parse that catches syntax errors safely. | No code is executed. Side-effect-free. |
| `wait*` | Waiting for background tasks (started via `run_in_background`) to complete. | The agent starts long-running commands in the background and MUST be able to block on their completion without operator approval. | Shell built-in. No file or network side-effects on its own; only observes child process state. |

### Python 🐍

| Permission | When | Why | Security |
|---|---|---|---|
| `python3*`, `python*` | Running Python scripts or the CLI modules inside the repository. | The project CLI (`cli/`) is Python-based and required for list, tree, deploy, and other targets. | Scoped to repository scripts. The agent MUST NOT install or run untrusted third-party packages without review. |
| `pip show*`, `pip list*` | Inspecting installed packages and versions. | Read-only introspection needed for dependency debugging. | No side-effects. Safe to allow unconditionally. |
| `pip install*` | Installing Python dependencies during environment setup. | Required by `make install-python` and related targets. | Modifies the virtual environment. Only packages declared in project requirements files SHOULD be installed. Arbitrary installs SHOULD be reviewed. |

### Ansible 📋

| Permission | When | Why | Security |
|---|---|---|---|
| `ansible-lint*` | Linting Ansible roles and playbooks. | Used by `make lint-ansible`. Read-only. | No playbook execution. Safe to allow unconditionally. |
| `ansible-inventory*` | Inspecting the Ansible inventory. | Required for debugging inventory structure. | Read-only. Safe to allow unconditionally. |
| `ansible --version*` | Verifying the installed Ansible version. | Read-only version check. | No side-effects. Safe to allow unconditionally. |
| `ansible-playbook --check*` | Dry-run execution of playbooks. | Does not apply changes to hosts. | Still connects to hosts and reads remote state. Ensure inventory targets are intended before running. |
| `ansible-playbook --syntax-check*` | Syntax validation of playbooks. | Parse-only. Does not connect to hosts. | No side-effects. Safe to allow unconditionally. |

### Docker 🐳

| Permission | When | Why | Security |
|---|---|---|---|
| `docker images*`, `docker ps*`, `docker inspect*`, `docker logs*` | Inspecting local images, running containers, and their logs. | Read-only status checks required for debugging. | No containers are started or modified. Safe to allow unconditionally. |
| `docker pull*` | Fetching images from a registry. | Required by `make build-dependency` and related targets. | Fetches external content. The source registry MUST be trusted before pulling. |
| `docker build*` | Building local images. | Required by `make build*` targets. | Executes the Dockerfile locally. Review Dockerfile changes before building. |
| `docker create*`, `docker export*` | Creating and exporting containers for inspection or archival. | Used in build and CI simulation workflows. | Local only. No network exposure from these operations alone. |
| `docker rm*`, `docker rmi*` | Removing containers and images. | Required for cleanup targets. | Destructive but scoped to local state only. Remote registries are not affected. |
| `docker compose*` | Managing the development stack defined in `compose.yml`. | Used by `make up`, `make down`, and related targets. | Can start services with volume mounts and network access. Changes to `compose.yml` MUST be reviewed before running the stack. |
| `docker exec*` | Running commands inside a running container. | Used by `make exec` for inspection and interactive debugging. | Grants shell access inside the container. MUST only be used on trusted, locally built containers. |

### Shell Utilities 🔧

| Permission | When | Why | Security |
|---|---|---|---|
| `grep*`, `find*`, `ls*`, `cat*`, `head*`, `tail*` | Reading and searching file content during any task. | Standard read-only inspection tools. Required for almost every task. | No write side-effects. Safe to allow unconditionally. |
| `wc*`, `sort*`, `jq*` | Counting lines, sorting output, parsing JSON. | Common pipeline utilities used in scripts and make targets. | No write side-effects. Safe to allow unconditionally. |
| `tar*` | Archiving files during build or export tasks. | Required by build and packaging scripts. | Can overwrite files when extracting. The sandbox `allowWrite` limits the blast radius to `.` and `/tmp`. |
| `mkdir*`, `cp*`, `mv*` | Creating directories and moving or copying files during setup and build tasks. | Required by install scripts and build targets. | `mv` and `cp` can overwrite files silently. Bounded by the sandbox `allowWrite` constraint. |

### Web Access 🌐

| Permission | When | Why | Security |
|---|---|---|---|
| `WebSearch` | Looking up documentation, error messages, or package information. | Allows the agent to resolve unknown APIs and tooling questions without leaving the terminal. | Outbound query only. No local data is uploaded. |
| `WebFetch(domain:github.com)`, `WebFetch(domain:raw.githubusercontent.com)`, `WebFetch(domain:api.github.com)` | Fetching repository pages, raw files, or GitHub API responses. | Required for tasks that inspect upstream code or release data. | Read-only. No credentials are transmitted. |
| `WebFetch(domain:docs.ansible.com)` | Fetching Ansible module and collection reference documentation. | Required when researching Ansible APIs. | Read-only. |
| `WebFetch(domain:docs.docker.com)` | Fetching Docker and Compose reference documentation. | Required when researching Docker APIs. | Read-only. |
| `WebFetch(domain:docs.gitea.com)` | Fetching Gitea self-hosted Git documentation. | Required when working on Gitea-related roles. | Read-only. |
| `WebFetch(domain:pypi.org)` | Fetching Python package metadata and version information. | Required for dependency research. | Read-only. |
| `WebFetch(domain:infinito.nexus)`, `WebFetch(domain:infinito.example)` | Accessing production and local development instances of this project. | Required for integration checks and live service inspection. | Read-only fetches. Credentials MUST NOT be embedded in fetched URLs. |
| `WebFetch(domain:docs.infinito.nexus)` | Fetching project documentation pages. | Required when cross-referencing published docs during tasks. | Read-only. |
| `WebFetch(domain:s.infinito.nexus)`, `WebFetch(domain:hub.infinito.nexus)` | Accessing project service endpoints. | Required for service-level inspection tasks. | Read-only. |
| `WebFetch(domain:cybermaster.space)` | Accessing the project operator domain referenced in role configuration. | Required when resolving operator-specific configuration. | Read-only. |
| `WebFetch(domain:community.taiga.io)` | Fetching Taiga project management documentation. | Required when working on Taiga-related roles. | Read-only. |
| `WebFetch(domain:monogramm.io)` | Fetching upstream Docker image documentation. | Required when researching images provided by this upstream. | Read-only. |
| `WebFetch(domain:ghcr.io)` | Fetching GitHub Container Registry image metadata. | Required for image version lookups. | Read-only. |
| `WebFetch(domain:letsencrypt.org)` | Fetching Let's Encrypt ACME documentation and root certificates. | Required when working on TLS-related roles. | Read-only. |
| `WebFetch(domain:hcaptcha.com)` | Fetching hCaptcha integration documentation. | Required when working on hCaptcha-related roles. | Read-only. |
| `WebFetch(domain:gstatic.com)` | Fetching Google static assets referenced by certain frontend roles. | Required when inspecting frontend asset behavior. | Read-only. |

## Ask Permissions ⚠️

These operations pause and require explicit operator approval before executing.

| Permission | When | Why approval is required | Security |
|---|---|---|---|
| `git commit*` | Creating a permanent history entry. | The operator MUST review the staged diff and message before committing. | Commits are persistent and visible to all contributors after push. |
| `git push*` | Publishing changes to the remote. | Cannot be undone without a force-push. | Exposes changes to all repository collaborators and CI. |
| `docker run*` | Starting a standalone container outside the compose stack. | Each invocation carries a unique risk profile depending on flags. | Can mount host paths, expose ports, and run privileged containers. |
| `curl*` | Making HTTP requests to arbitrary URLs. | Can transmit environment variables and credentials to external endpoints. | Risk depends entirely on the URL and flags used. Every invocation MUST be reviewed. |
| `gh api*` | Making direct GitHub REST or GraphQL API calls. | Can modify branch protection, secrets, webhooks, collaborators, and workflow triggers. | Supports arbitrary HTTP methods (`-X POST/PATCH/DELETE`). Each invocation MUST be reviewed individually. |

## Deny Rules 🚫

These operations are unconditionally blocked, regardless of any `allow` entry.

| Permission | Reason |
|---|---|
| `git push --force*` | Rewrites remote history. Can permanently destroy other contributors' work. |
| `git reset --hard*` | Discards all uncommitted local changes without any recovery path. |
| `rm -rf*` | Recursive force-delete with no confirmation and no undo. |
| `sudo*` | Prevents privilege escalation to root on the host system. |

## Sandbox 🏖️

### Write Scope

The agent MAY write to `.` (the repository root) and `/tmp`. All other paths are read-only by default.

### Read Restrictions

The following directories are never readable, even if a task explicitly requests access:

| Path | What it protects |
|---|---|
| `~/.ssh` | SSH private keys. |
| `~/.gnupg` | GPG keys and keyrings. |
| `~/.kube` | Kubernetes cluster credentials. |
| `~/.aws` | AWS access keys and configuration. |
| `~/.config/gcloud` | Google Cloud service account credentials. |

## Local Overrides 🖥️

Contributors MAY extend project permissions via `.claude/settings.local.json`. This file is git-ignored and applies only to the local machine.

| Rule | Description |
|---|---|
| MUST NOT weaken `deny` | Local overrides cannot lift unconditional blocks defined in `settings.json`. |
| Machine-specific entries MUST stay local | Absolute paths, process IDs, and debug tooling MUST NOT be promoted to `settings.json`. |
| Shared permissions SHOULD be promoted | Permissions useful for all contributors SHOULD be added to `settings.json` instead of staying local. |
| Keep overrides minimal | Entries already covered by project-level wildcards SHOULD be removed from `settings.local.json`. |
