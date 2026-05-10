# To-dos

- The generic playwright biber and administrator personas are blocked via `PERSONA_BIBER_BLOCKED=true` and `PERSONA_ADMINISTRATOR_BLOCKED=true` in `templates/playwright.env.j2` (req 019 Rule 11 explicit opt-out). Bookwyrm's logout control is inside an icon-only profile-avatar dropdown the generic in-app logout helper cannot match. Once upstream adds an accessible label on the avatar trigger or a per-role logout helper lands, drop both opt-out flags and let the persona helpers drive the dashboard → app → logout journey end-to-end.
