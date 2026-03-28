[Back to Languages](README.md)

# Shell

Use this page for shell-script-specific guidance.

## Script Layout

- You MUST store general `.sh` scripts for infinito.nexus administration under `scripts/`.
- You MUST keep shell entrypoints in `scripts/` so they stay easy to discover and reuse.
- You MUST keep role-local or component-specific shell helpers in their owning area, such as `roles/.../files/`, when they belong to a single role.

## Executable Bit

- You MUST set the executable bit on shell scripts that are meant to run directly.
- You MUST use `chmod +x` for those scripts so they can be invoked as executables.
- You MUST keep a shebang at the top of executable shell scripts.

## Notes

- `scripts/tests/deploy/local/exec/container.sh` is a direct-entry shell script example.
- For shell entrypoints that are exposed through `make`, you SHOULD prefer a thin target that delegates to the script.
