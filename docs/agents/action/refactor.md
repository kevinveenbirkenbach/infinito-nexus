[Back to AGENTS hub](../../../AGENTS.md)

# Refactoring and Optimization

## After Every Commit

After every commit you MUST ask the user:

> "Do you want to refactor and optimize the affected files?"

- If the user answers **no**, continue without refactoring.
- If the user answers **yes**, follow the steps below.

## Refactoring Steps

1. Re-read `AGENTS.md` and follow all instructions in it before proceeding.
2. Apply all rules from `AGENTS.md` and `docs/contributing/` to every affected file — not only code rules, but also documentation, naming, structure, and any other applicable guidelines.
3. If the change affects an Ansible role, you MUST refactor and optimize the **entire role**, not only the files that were directly modified.
