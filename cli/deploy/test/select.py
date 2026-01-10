from __future__ import annotations

from typing import Iterable


def filter_allowed_workstation(app_ids: Iterable[str]) -> list[str]:
    # keep your existing workstation selection:
    # desk-* and util-desk-*
    out: list[str] = []
    for a in app_ids:
        if a.startswith("desk-") or a.startswith("util-desk-"):
            out.append(a)
    return out


def filter_allowed_server(app_ids: Iterable[str]) -> list[str]:
    # server deploy test for invokable web-app-* and web-svc-*
    out: list[str] = []
    for a in app_ids:
        if a.startswith("web-app-") or a.startswith("web-svc-"):
            out.append(a)
    return out
