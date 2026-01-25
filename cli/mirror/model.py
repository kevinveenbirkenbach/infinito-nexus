from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageRef:
    role: str  # e.g. svc-db-postgres
    service: str  # e.g. postgres
    name: str  # canonical image name, e.g. postgis/postgis or postgres
    version: str  # e.g. 17-3.5
    source: (
        str  # docker hub source ref, e.g. postgis/postgis:17-3.5 or library/postgres:16
    )
