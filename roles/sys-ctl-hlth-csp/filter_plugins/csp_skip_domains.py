import sys
from collections.abc import Mapping
from pathlib import Path

from utils.roles.applications.config import get  # reuse existing helper

# Role-bundled plugin: Ansible loads by file path with no package
# context, so `from . import PROJECT_ROOT` cannot resolve here.
# nocheck: project-root-import
_BASE_DIR = str(Path(__file__).resolve().parents[3])
_MODULE_UTILS_DIR = str(Path(_BASE_DIR) / "utils")
for _p in (_BASE_DIR, _MODULE_UTILS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _to_list(x):
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    if isinstance(x, (list, tuple, set)):
        out = []
        for v in x:
            if isinstance(v, (list, tuple, set)):
                out.extend(_to_list(v))
            elif isinstance(v, str):
                out.append(v)
            elif isinstance(v, Mapping):
                out.extend(_to_list(list(v.values())))
        return out
    if isinstance(x, Mapping):
        out = []
        for v in x.values():
            out.extend(_to_list(v))
        return out
    return []


def _has_code_ge_400(codes):
    if codes is None:
        return False
    if not isinstance(codes, (list, tuple, set)):
        codes = [codes]
    for c in codes:
        try:
            n = int(c)
        except (TypeError, ValueError):
            continue
        if n >= 400:
            return True
    return False


def csp_skip_domains(applications, group_names=None):
    """Return canonical+alias domains of every selected application
    whose ``server.status_codes.default`` declares any HTTP code >= 400.

    The csp-checker container treats any non-reachable / non-2xx-3xx
    response as a failure ("Unable to reach ..."), but federation-only
    roles (e.g. web-app-bridgy-fed) legitimately serve a 4xx at `/`.
    Those domains are excluded here so the CSP probe does not fail
    on a contractually-correct response.
    """
    if not isinstance(applications, Mapping):
        return []

    if isinstance(group_names, (list, set, tuple)):
        selection = {str(x) for x in group_names if str(x)}
    elif isinstance(group_names, str):
        selection = {g.strip() for g in group_names.split(",") if g.strip()}
    else:
        selection = set()

    skip = set()
    for app_id in applications:
        if selection and app_id not in selection:
            continue
        default = get(
            applications,
            app_id,
            "server.status_codes.default",
            strict=False,
            default=None,
        )
        if not _has_code_ge_400(default):
            continue
        canonical = get(
            applications, app_id, "server.domains.canonical", strict=False, default=[]
        )
        aliases = get(
            applications, app_id, "server.domains.aliases", strict=False, default=[]
        )
        for d in _to_list(canonical) + _to_list(aliases):
            if d:
                skip.add(d)

    return sorted(skip)


class FilterModule:
    def filters(self):
        return {"csp_skip_domains": csp_skip_domains}
