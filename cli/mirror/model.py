from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageRef:
    role: str  # e.g. svc-db-postgres
    service: str  # e.g. postgres
    name: str  # canonical image name, e.g. postgis/postgis or postgres
    version: str  # e.g. 17-3.5
    source: str  # full pull ref, e.g. docker.io/library/postgres:16 or quay.io/keycloak/keycloak:latest
    registry: str = (
        "docker.io"  # source registry hostname, e.g. docker.io, quay.io, ghcr.io
    )
