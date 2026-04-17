# Push, Trigger, Pull

## 1. Free runners

Enumerate every in-progress run across the repository, regardless of branch:

```
gh run list --status in_progress --limit 200 --json databaseId,name,displayTitle,headBranch,workflowName,event,createdAt,url
```

Present the list to the operator and ask which runs should be cancelled to free runners: all, a specific subset, or none. Cancel only what the operator names, one call per id:

```
gh run cancel <id>
```

MUST NOT batch through a shell loop (see CLAUDE.md loop prohibition). If the operator answers *"none"*, skip to step 2.

## 2. Push

Target `<branch>` is the branch the operator names; if none is named, use the current branch (`git rev-parse --abbrev-ref HEAD`). All subsequent steps operate on the same `<branch>`.

```
git push -u origin <branch>
```

## 3. Draft the PR

```
gh pr list --head <branch> --state open --json number,isDraft,url
```

- No PR: create it as draft via `gh pr create --draft` using the matching template per [pull-request.md](./pull-request.md).
- PR exists and is open: `gh pr ready --undo <number>`.
- PR exists and is already draft: no action.

## 4. Trigger Manual CI

Compute scope from `git diff --name-only origin/main...HEAD`.

- `whitelist`: set to the single role id only if the diff is confined to one `roles/<role>/`; otherwise omit so all roles run.
- `distros`: pass a space-separated list only if the diff is distro-specific; otherwise omit to run the full default set.

```
gh workflow run entry-manual.yml --ref <branch> \
  [-f distros="<distros>"] \
  [-f whitelist="<role>"]
```

Watch with `gh run watch`.

## 5. Close the loop

- On `success`: `gh pr ready <number>` to mark the PR ready for review.
- On failure: ask the operator whether to follow [pipeline.md](./debug/pipeline.md). MUST NOT mark the PR ready for review while the last CI run is failing.
