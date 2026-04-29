"""Compose-profile selection for the dev/CI stack.

Single source of truth for which `docker compose --profile ...` flags
the dev tooling passes through. Lives in its own module so callers
(`Compose` in compose.py, `_compose_run` in down.py) cannot drift on
which services belong to a given run.

The decision is based on the runtime environment, not on the call
site:

* ``ci``   - always active. Carries `coredns`, `infinito` and any
             other future "always present" service.
* cache    - active on developer machines, inactive on CI runners.
             Local hosts amortize the cache services across many runs
             (cross-run image dedup, cross-run package-manager dedup);
             CI runners get a fresh disk per job, so the proxies add
             startup latency without payoff. The decision is exposed
             via ``registry_cache_active()``; the cache stack itself
             is gated by file inclusion (the dev tooling layers
             ``compose/cache.override.yml`` only when active), so no
             dedicated ``--profile cache`` flag is emitted.
"""

from __future__ import annotations

import os


class Profile:
    """Decide which docker compose profiles to activate."""

    def is_ci(self) -> bool:
        """True when running on a CI runner (GitHub-hosted or generic).

        Conservative on purpose: if any of the standard CI signals are
        set, treat the environment as CI. ``act`` runs locally but
        sets ``GITHUB_ACTIONS=true`` to mimic the runner; for the
        registry-cache decision that is the same answer either way.
        """
        return (
            os.environ.get("GITHUB_ACTIONS") == "true"
            or os.environ.get("RUNNING_ON_GITHUB") == "true"
            or os.environ.get("CI") == "true"
        )

    def registry_cache_active(self) -> bool:
        """True iff the `cache` profile should be activated.

        Inverse of ``is_ci``: developer machines benefit from the
        proxy's cross-run image dedup, CI runners do not.
        """
        return not self.is_ci()

    def args(self) -> list[str]:
        """The ``--profile ...`` flag list to pass to docker compose.

        Only ``--profile ci`` is emitted; the cache stack is gated by
        compose-file inclusion (``compose/cache.override.yml``) and
        does not carry a profile attribute, so a ``--profile cache``
        flag would be a no-op.
        """
        return ["--profile", "ci"]
