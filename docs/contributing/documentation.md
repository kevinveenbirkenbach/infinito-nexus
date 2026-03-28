[Back to CONTRIBUTING hub](../../CONTRIBUTING.md)

# Documentation

All project documentation should be reachable at [docs.infinito.nexus](https://docs.infinito.nexus/).

## Markdown

- Keep core information inside the repository, either in code or in `.md` files.
- Use `.md` files for commands, workflows, setup, and contributor guidance.
- Do not use `.md` files to describe implementation logic that is already visible in the code.
- Prefer `README.md` for directory-level documentation when a human-facing entry point already exists.

## Comments

- Write code so it is logical and self-explanatory and usually does not need comments.
- Add code comments only when an exception, edge case, or surprising decision would otherwise confuse readers.
- Use comments to explain why something is unusual, not to restate what obvious code already does.
- When keeping an intentionally retained outdated version pin, document the exception at the pin site with a local `TODO` comment in the file's normal comment style (`#todo`, `# TODO`, or similar) and explain why it remains pinned so the root cause stays visible until it can be fixed.


## Requirement Keywords (RFC 2119)

You MUST use [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) keywords in documentation and agent instructions to express requirement levels unambiguously:

| Keyword | Meaning |
|---|---|
| `MUST` / `REQUIRED` / `SHALL` | Absolute requirement — no deviation allowed. |
| `MUST NOT` / `SHALL NOT` | Absolute prohibition — never do this. |
| `SHOULD` / `RECOMMENDED` | Strongly recommended — deviation requires justification. |
| `SHOULD NOT` / `NOT RECOMMENDED` | Strongly discouraged — allowed only with justification. |
| `MAY` / `OPTIONAL` | Permitted but not required. |

Apply these keywords in `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and all files under `docs/agents/` so that requirement strength is always unambiguous.

## Links

- You MUST NOT use the full URL as link text. Use the domain name, `here`, or the filename instead — never the full path.
- For communication links such as Matrix, email, or phone, you MUST show only the value itself as link text, without any protocol prefix or URL wrapper.

| Type | MUST NOT | MUST |
|---|---|---|
| Web link | `https://docs.infinito.nexus/setup` | `docs.infinito.nexus`, `here`, a descriptive label, or `setup.md` |
| File link | `docs/contributing/flow/workflow.md` | `workflow.md` or `Contribution Flow` |
| Email | `mailto:hello@infinito.nexus` | `hello@infinito.nexus` |
| Matrix | `https://matrix.to/#/@user:infinito.nexus` | `@user:infinito.nexus` |
| Phone | `tel:+491234567890` | `+49 123 456 7890` |

## Semantics and Writing

- Keep code and comments in English.
- Fix nearby wording and semantic issues when you touch a file, and correct obvious nearby issues proactively in the same pass.
- Use emojis when they make the text more visually appealing, improve the mood, and increase readability.

## Documentation Structure

### Markdown

- Prefer `README.md` for directory-level documentation when a human-facing entry point already exists.

### Sphinx

- If a documentation directory does not already have a `README.md`, add an `index.rst` where it helps automated docs generation.
- Keep Sphinx-friendly directory indexes up to date so the published documentation can include new content without extra wiring.
