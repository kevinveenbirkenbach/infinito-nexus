[Back to CONTRIBUTING hub](../../CONTRIBUTING.md)

# Coding Standards

This repository values simple, maintainable, and well-tested changes.

## Principles

Follow these principles. Keep the rule column short, imperative, and as [SMART](https://en.wikipedia.org/wiki/SMART_criteria) as practical; use the reason column for the rationale, the principle column for the linked source name, and put the expanded wording in the details column.

| Rule | Reason | Principle | Details |
|---|---|---|---|
| Consolidate duplicate logic before merging. | Duplicate behavior is easier to keep consistent. | [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself) | Keep one implementation for each behavior and remove repeated logic from the touched files. |
| Leave touched code cleaner than you found it. | Small cleanup reduces future friction. | [Boy Scout Rule](https://en.wikipedia.org/wiki/Leaving_the_world_a_better_place) | Make small, safe cleanup improvements in the files you touch when they reduce friction without expanding the scope unnecessarily. |
| Store each shared value once. | Shared values drift when copied. | [SPOT](https://en.wikipedia.org/wiki/Single_source_of_truth) | Put shared fixed values in one canonical source and reference them everywhere else. |
| Choose the simplest solution. | Simple code is easier to change. | [KISS](https://en.wikipedia.org/wiki/KISS_principle) | Prefer the smallest implementation that still satisfies the requirement and remains easy to maintain. |
| Make prompts SMART. | Clear prompts reduce ambiguity. | [SMART](https://en.wikipedia.org/wiki/SMART_criteria) | Write prompts that are specific, measurable, achievable, relevant, and time-bound so the agent can act on them without ambiguity. |
| Ship the first valuable increment early. | Early value shortens feedback loops. | [Agile Manifesto](https://agilemanifesto.org/) | Deliver working software as soon as it is useful and keep delivering value continuously. |
| Accept useful requirement changes. | Better ideas can arrive late. | [Agile Manifesto](https://agilemanifesto.org/) | Treat late requirement changes as normal when they improve customer value. |
| Release working software frequently. | Frequent delivery surfaces issues sooner. | [Agile Manifesto](https://agilemanifesto.org/) | Keep iterations short enough that users see working software at regular intervals. |
| Work with business daily. | Daily contact keeps intent aligned. | [Agile Manifesto](https://agilemanifesto.org/) | Keep business and development in daily contact for decisions and feedback. |
| Trust motivated people. | Engaged people take better ownership. | [Agile Manifesto](https://agilemanifesto.org/) | Build around engaged people and give them ownership of the work. |
| Use direct conversation for blocking topics. | Direct talk resolves blockers faster. | [Agile Manifesto](https://agilemanifesto.org/) | Prefer face-to-face or synchronous discussion when the decision is urgent or complex. |
| Measure progress with working software. | Working software shows real progress. | [Agile Manifesto](https://agilemanifesto.org/) | Use running software, not documents alone, as the main progress signal. |
| Keep a sustainable pace. | Sustainable pace avoids burnout. | [Agile Manifesto](https://agilemanifesto.org/) | Set a pace the team can maintain for the long term. |
| Improve technical quality continuously. | Quality debt compounds if ignored. | [Agile Manifesto](https://agilemanifesto.org/) | Invest in design and code quality on every change. |
| Remove unnecessary work. | Removing work leaves room for value. | [Agile Manifesto](https://agilemanifesto.org/) | Choose the smallest solution that achieves the goal. |
| Let teams shape their own design. | Local teams know the best design. | [Agile Manifesto](https://agilemanifesto.org/) | Let self-organizing teams own architecture, requirements, and implementation. |
| Inspect and adapt regularly. | Regular review catches process drift. | [Agile Manifesto](https://agilemanifesto.org/) | Review the process at regular intervals and change it when it is not working. |
| Write the failing test first. | Failing tests confirm requirements first. | [TDD](https://en.wikipedia.org/wiki/Test-driven_development) | Start with a failing test, implement the minimum code, and refactor with confidence. |
| Prefer beautiful code. | Readable code is easier to trust. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Choose code that is clean, coherent, and pleasant to read instead of code that is only clever. |
| Prefer explicit behavior. | Explicit behavior is easier to reason about. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Make behavior visible in the code instead of relying on hidden assumptions. |
| Mark intentional exceptions. | Exceptions need context. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Document intentional exceptions close to the relevant code so they stay visible until they can be removed. |
| Prefer simple code. | Simple code changes more safely. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Choose the simplest solution that still does the job. |
| Prefer manageable complexity. | Controlled complexity keeps maintenance cost down. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Keep complexity under control instead of making the solution more complicated than needed. |
| Prefer flat structures. | Shallow structures are easier to scan. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Keep control flow and data structures shallow when a flatter shape works. |
| Prefer sparse structures. | Sparse layouts make intent clearer. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Avoid dense packing when a clearer, more spacious layout improves understanding. |
| Make code readable. | Readable code speeds review and debugging. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Write code so the next person can understand it quickly. |
| Protect the rules from exceptions. | Contained exceptions keep rules useful. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Handle special cases without breaking the general rule set. |
| Prefer practical solutions. | Practical code works in the real repo. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Choose the option that works well in practice over one that is only theoretically pure. |
| Fail loudly on errors. | Hidden failures cause harder incidents later. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Do not let unexpected errors disappear unnoticed. |
| Silence errors only intentionally. | Suppressed errors need justification. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Suppress errors only when you can explain why that is safe. |
| Refuse to guess in ambiguity. | Clarification is safer than guessing. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Stop and clarify when the inputs or intent are unclear. |
| Choose one obvious way. | One standard path lowers cognitive load. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Prefer one clear, standard path over multiple equivalent ones. |
| Make the obvious path obvious. | The right choice should be easiest. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Shape the code so the recommended approach is the easiest to see. |
| Act now when action is due. | Deferred work tends to grow. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Do the needed work now instead of deferring it without reason. |
| Wait rather than rush. | Premature action can make the result worse. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Pause when acting immediately would make the result worse. |
| Keep hard code easy to explain. | Hard-to-explain code often hides flaws. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | If the code is hard to explain, rework it before merging. |
| Keep easy code easy to explain. | Easy-to-explain code is usually sound. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | If the code is easy to explain, it is likely a good idea. |
| Use namespaces generously. | Namespaces prevent collisions in a large repo. | [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) | Group names so they do not collide and remain easy to navigate. |

## Diff Quality

- Keep diffs focused, readable, and easy to review.
- Avoid duplicate, conflicting, or purely cosmetic churn unless formatting cleanup is part of the task.
- Prefer semantic improvements that reduce maintenance effort.

## Lint

Use these linting and quality tools where applicable:

- [ruff](https://github.com/astral-sh/ruff)
- [shellcheck](https://github.com/koalaman/shellcheck)
- [hadolint](https://github.com/hadolint/hadolint)

## Refactoring

- If you touch a file, refactor it according to these coding standards where practical.
- If similar logic exists elsewhere in the project, refactor it toward a shared implementation.

## Ansible

Use this section for Ansible-specific guidance that applies across the repository.

### Common

Use these shared rules as the default baseline for role values and path handling.

### Paths

Build filesystem paths with `path_join` instead of concatenating path segments as strings.

### Variables and Constants

These rules keep shared role values explicit, reusable, and easy to read.

- Prefer defining shared fixed role variables once in `vars/main.yml` as the single source of truth instead of recomputing them with `lookup()` or dotted variable composition in `*.j2` or `*.yml`.
- Variables that are defined once and treated as constants must be uppercase.

### Role Design

Use this section for role-structure guidance around images, files, and constants.

#### Container Images

Use this rule when a role needs a Docker image definition.

- Prefer `Dockerfile` over `Dockerfile.j2`; only use `Dockerfile.j2` when build-time templating is genuinely required.

For documentation, comments, semantics, and writing guidance, see [Documentation](documentation.md).

For test commands and testing standards, see [Testing and Validation](testing.md).
