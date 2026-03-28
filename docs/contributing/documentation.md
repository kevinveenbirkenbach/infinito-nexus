# Documentation

All project documentation MUST be reachable at [docs.infinito.nexus](https://docs.infinito.nexus/).

## Markdown

- You MUST keep core information inside the repository, either in code or in `.md` files.
- You MUST use `.md` files for commands, workflows, setup, and contributor guidance.
- You MUST NOT use `.md` files to describe implementation logic that is already visible in the code.

## Comments

- You SHOULD write code so it is logical and self-explanatory and usually does not need comments.
- You MUST add code comments only when an exception, edge case, or surprising decision would otherwise confuse readers.
- You MUST use comments to explain why something is unusual, not to restate what obvious code already does.
- When keeping an intentionally retained outdated version pin, you MUST document the exception at the pin site with a local `TODO` comment in the file's normal comment style (`#todo`, `# TODO`, or similar) and explain why it remains pinned so the root cause stays visible until it can be fixed.

## Requirement Keywords (RFC 2119)

You MUST use [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) keywords in all documentation to express requirement levels unambiguously:

| Keyword | Meaning |
|---|---|
| `MUST` / `REQUIRED` / `SHALL` | Absolute requirement — no deviation allowed. |
| `MUST NOT` / `SHALL NOT` | Absolute prohibition — never do this. |
| `SHOULD` / `RECOMMENDED` | Strongly recommended — deviation requires justification. |
| `SHOULD NOT` / `NOT RECOMMENDED` | Strongly discouraged — allowed only with justification. |
| `MAY` / `OPTIONAL` | Permitted but not required. |

## Links

- You MUST NOT use the full URL as link text. Use the domain name, `here`, or the filename instead — never the full path.
- After `See`, you MUST use the domain name as link text, not `here`. `here` is only acceptable when the surrounding sentence reads naturally with it (e.g. "More information [here](...)").
- For communication links such as Matrix, email, or phone, you MUST show only the value itself as link text, without any protocol prefix or URL wrapper.

| Type | MUST NOT | MUST |
|---|---|---|
| Web link | `https://docs.infinito.nexus/setup` | `docs.infinito.nexus`, `here`, a descriptive label, or `setup.md` |
| File link | `docs/contributing/flow/workflow.md` | `workflow.md` or `Contribution Flow` |
| Email | `mailto:hello@infinito.nexus` | `hello@infinito.nexus` |
| Matrix | `https://matrix.to/#/@user:infinito.nexus` | `@user:infinito.nexus` |
| Phone | `tel:+491234567890` | `+49 123 456 7890` |

## Semantics and Writing

- You MUST keep code and comments in English.
- You MUST fix nearby wording and semantic issues when you touch a file, and correct obvious nearby issues proactively in the same pass.
- You SHOULD use emojis when they make the text more visually appealing, improve the mood, and increase readability.

## Documentation Structure

### Markdown

- You SHOULD prefer `README.md` for directory-level documentation when a human-facing entry point already exists.

### Sphinx

- If a documentation directory does not already have a `README.md`, you SHOULD add an `index.rst` where it helps automated docs generation.
- You MUST keep Sphinx-friendly directory indexes up to date so the published documentation can include new content without extra wiring.
