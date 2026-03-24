# Agent Instructions

## Code Quality

Follow this principles:

- [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself) - If code occures >1 refactor it to a [SPOT](https://en.wikipedia.org/wiki/Single_source_of_truth)
- [KISS](https://en.wikipedia.org/wiki/KISS_principle)
- [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python)

## Semantic
- Solve semantic errors whenever you find them

## Debugging
- Logs are placed in *job-logs.txt or in *.log files
- Logs MUST never be committed

## Commiting
- Verify before every commit with `make test`
- If fails execute: `make clean-sudo` and afterwards `make test` again

## Help

### Locale Development Environment
If a user has problems in setting up the local dev environment read the commands from the following file to help him:

- [Makefile](Makefile)
- [development.sh](scripts/tests/development.sh) 

## About AGENTS.md
- https://agents.md/
- https://s.infinito.nexus/aibestpractice
