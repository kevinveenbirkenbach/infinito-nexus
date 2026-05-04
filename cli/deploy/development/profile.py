"""Compose-profile selection for the dev/CI stack."""

from __future__ import annotations

import os


class Profile:
    """Decide which docker compose profiles to activate."""

    def is_ci(self) -> bool:
        """True when any standard CI signal is set."""
        return (
            os.environ.get("GITHUB_ACTIONS") == "true"
            or os.environ.get("RUNNING_ON_GITHUB") == "true"
            or os.environ.get("CI") == "true"
        )

    def registry_cache_active(self) -> bool:
        """True iff the cache stack should be loaded (local dev only)."""
        return not self.is_ci()

    def args(self) -> list[str]:
        """`--profile` flags. Cache stack is gated by file inclusion, not a flag."""
        return ["--profile", "ci"]
