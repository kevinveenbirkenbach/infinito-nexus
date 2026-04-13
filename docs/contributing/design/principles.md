# Code Principles 📐

Use these principles when you change repository code, scripts, or automation.
For organisational and team-process principles, see [principles.md](../organisation/principles.md).

## Principles 📋

Follow these principles. Keep the rule column short, imperative, and as [SMART](https://en.wikipedia.org/wiki/SMART_criteria) as practical; use the reason column for the rationale, the principle column for the linked source name, and put the expanded wording in the details column.

| Rule | Reason | Principle | Details |
|---|---|---|---|
| Consolidate duplicate logic before merging. | Duplicate behavior is easier to keep consistent. | [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself) | Keep one implementation for each behavior and remove repeated logic from the touched files. |
| Leave touched code cleaner than you found it. | Small cleanup reduces future friction. | [Boy Scout Rule](https://en.wikipedia.org/wiki/Leaving_the_world_a_better_place) | Make small, safe cleanup improvements in the files you touch when they reduce friction without expanding the scope unnecessarily. |
| Store each shared value once. | Shared values drift when copied. | [SPOT](https://en.wikipedia.org/wiki/Single_source_of_truth) | Put shared fixed values in one canonical source and reference them everywhere else. |
| Choose the simplest solution. | Simple code is easier to change. | [KISS](https://en.wikipedia.org/wiki/KISS_principle) | Prefer the smallest implementation that still satisfies the requirement and remains easy to maintain. |
| Give each module one reason to change. | Focused modules are easier to test and replace. | [SRP](https://en.wikipedia.org/wiki/Single-responsibility_principle) | Each module, class, or function MUST have exactly one responsibility so that changes to one concern do not ripple into unrelated code. |
| Make prompts SMART. | Clear prompts reduce ambiguity. | [SMART](https://en.wikipedia.org/wiki/SMART_criteria) | Write prompts that are specific, measurable, achievable, relevant, and time-bound so the agent can act on them without ambiguity. |
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

For code quality rules, see [lint.md](../actions/testing/lint.md).
For framework-specific guidance, see [ansible.md](../tools/ansible.md) and [make.md](../tools/make.md).
