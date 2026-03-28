[Back to Languages](README.md)

# Shell

Use this page for shell-script-specific guidance.

## Script Layout

- Store general `.sh` scripts for infinito.nexus administration under `scripts/`.
- Keep shell entrypoints in `scripts/` so they stay easy to discover and reuse.
- Keep role-local or component-specific shell helpers in their owning area, such as `roles/.../files/`, when they belong to a single role.

## Executable Bit

- Set the executable bit on shell scripts that are meant to run directly.
- Use `chmod +x` for those scripts so they can be invoked as executables.
- Keep a shebang at the top of executable shell scripts.

## Notes

- `scripts/tests/deploy/local/inspect.sh` is a direct-entry shell script example.
- For shell entrypoints that are exposed through `make`, prefer a thin target that delegates to the script.
