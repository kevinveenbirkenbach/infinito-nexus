from __future__ import annotations

import subprocess


def resolve_run_after(role_name: str) -> list[str]:
    """
    Calls your existing resolver:
      python -m cli.meta.applications.run_after_resolution <role_name>

    Returns a list of role folder names (e.g., web-app-foo web-svc-bar ...)
    """
    cmd = ["python3", "-m", "cli.meta.applications.run_after_resolution", role_name]
    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"run_after_resolution failed for {role_name} (rc={r.returncode})\n"
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
    # ensure prerequisites first + app_id last
    out: list[str] = []
    for d in deps_role_names:
        if d != app_id and d not in out:
            out.append(d)
    if app_id not in out:
        out.append(app_id)
    return out
