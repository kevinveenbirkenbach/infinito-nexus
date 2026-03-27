# Agent Instructions

- Treat `AGENTS.md` as the repository-wide source of truth for agent instructions.
- Use [CONTRIBUTING.md](../../CONTRIBUTING.md) as the SPOT for contributor workflow, testing, review, and coding standards.
- Recursively scan repository `.md` files for applicable instructions, apply each file once, and skip already visited paths to avoid infinite loops.
- Apply the rules in the `Principles` table in [CONTRIBUTING.md](../../CONTRIBUTING.md); map the `Rule` column to the action and the `Details` column to the full guidance.
- Let `CLAUDE.md` and `GEMINI.md` extend these rules without contradiction.
- Read [docs/agents/README.md](docs/agents/README.md) for the detailed agent index.
