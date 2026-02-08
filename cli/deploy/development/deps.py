# cli/deploy/development/deps.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import only for type checking to avoid runtime import cycles.
    from .compose import Compose


def resolve_run_after(compose: "Compose", role_name: str) -> list[str]:
    """
    Calls resolver inside the infinito container:
      python -m cli.meta.applications.resolution.combined <role_name>
    """
    cmd = ["python3", "-m", "cli.meta.applications.resolution.combined", role_name]
    r = compose.exec(cmd, check=False, workdir="/opt/src/infinito", capture=True)

    if r.returncode != 0:
        raise RuntimeError(
            f"resolution.combined failed for {role_name} (rc={r.returncode})\n"
            f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        )

    txt = (r.stdout or "").strip()
    if not txt:
        return []
    return [t for t in txt.split() if t.strip()]


def apps_with_deps(app_id: str, deps_role_names: list[str]) -> list[str]:
    """
    The resolver returns role folder names. In your current inventory groups,
    group names == application_ids (folder names). So we can include them directly.
    """
    out: list[str] = []
    for d in deps_role_names:
        if d != app_id and d not in out:
            out.append(d)
    if app_id not in out:
        out.append(app_id)
    return out
