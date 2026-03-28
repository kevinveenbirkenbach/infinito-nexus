[Back to Role Files](README.md)

# style.css

This page is the SPOT for automatically generating and updating role-local `style.css`, `style.css.j2`, and equivalent CSS entry files.
Use this page for implementation scope, override strategy, and live review.
For repository wiring, inventory keys, and the generated palette contract, see [Contributing `style.css`](../../../contributing/code/role/style.css.md).

## Goal

- Start from the role's existing CSS and add the smallest possible theming layer on top of it.
- Prefer token mapping over large selector rewrites so the role keeps its native structure and behavior.
- Write the result so it feels like one coherent brand theme instead of a collection of unrelated overrides.

## Replace

- Replace hard-coded visual values that define the role's look and feel: colors, RGB channels, gradients, borders, shadows, overlays, placeholder colors, focus colors, and similar theme tokens.
- Replace framework or app-specific theme variables with values derived from the repository's generated palette, typically `--color-01-*` and `--color-01-rgb-*`, when such variables already exist.
- Replace direct color usage in selectors only when variable mapping is not sufficient to reach the affected surface.
- Replace related values together. If a surface color changes, also review the matching text color, border color, hover state, active state, disabled state, and transparency values.
- Replace RGB helper variables together with their solid color counterparts when the target role uses alpha-based effects such as `rgba(...)`, overlays, or translucent backgrounds.

## Do Not Replace

- Do not replace layout, spacing, sizing, positioning, z-index, overflow, animation timing, or component structure unless the visual requirement truly depends on it.
- Do not replace semantic behavior, JavaScript hooks, state logic, or framework-specific class wiring just to apply branding.
- Do not replace existing semantic variables with hard-coded literals when the same effect can be achieved by mapping the variables correctly.
- Do not rewrite large upstream style blocks when a focused override or token remapping is enough.
- Do not introduce app-specific assumptions into this workflow. Inspect the target role first and adapt to its real variable names and component model.

## Workflow

- Pull in or preserve the role's regular CSS first so the base application styling stays intact.
- Inspect which variables the target role or framework already exposes, for example semantic tokens, framework palette variables, or role-local custom properties.
- Map the generated repository palette, typically `--color-01-*` and `--color-01-rgb-*`, onto those existing variables before adding selector-level overrides.
- Add selector-level overrides only for surfaces that cannot be themed through variables alone.
- Keep gradients, transparency, text contrast, and surface hierarchy aligned so the themed role still reads as one system.

## Review

- Check that primary actions, links, forms, cards, dialogs, navigation, and overlays still belong to the same visual system.
- Check that readable contrast remains intact for normal, hover, focus, active, and disabled states.
- Check the result with live inspection in the running application, not only by reading the CSS or generated files.
- Compare the implemented styling against the rendered UI so mismatches between intended tokens and actual browser output become visible.
- At minimum, inspect and compare the start page and the login page because both usually expose the most important shared surfaces, text colors, forms, and navigation patterns.
- If the change affects user-visible behavior, add or update the matching end-to-end coverage in [Role `playwright.spec.js`](playwright.spec.js.md).
- Check that the final CSS still looks like a themed version of the target application, not a forked redesign.
