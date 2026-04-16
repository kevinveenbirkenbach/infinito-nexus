# Debugging

This directory documents how agents MUST debug failures during agent work.
Its scope covers three independent workflows: local deploys (debugged from live local output and local logs), GitHub Actions / CI run failures (fully automated triage that fetches logs and artefacts itself via `gh`), and ad-hoc inspection of log files manually placed in the repository workdir by the operator.
