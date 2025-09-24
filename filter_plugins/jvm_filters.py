from __future__ import annotations

import sys, os, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ansible.errors import AnsibleFilterError
from module_utils.config_utils import get_app_conf
from module_utils.entity_name_utils import get_entity_name

_UNIT_RE = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*([kKmMgGtT]?[bB]?)?\s*$')
_FACTORS = {
    '': 1, 'b': 1,
    'k': 1024, 'kb': 1024,
    'm': 1024**2, 'mb': 1024**2,
    'g': 1024**3, 'gb': 1024**3,
    't': 1024**4, 'tb': 1024**4,
}

def _to_bytes(v: str) -> int:
    if v is None:
        raise AnsibleFilterError("jvm_filters: size value is None")
    s = str(v).strip()
    m = _UNIT_RE.match(s)
    if not m:
        raise AnsibleFilterError(f"jvm_filters: invalid size '{v}'")
    num, unit = m.group(1), (m.group(2) or '').lower()
    try:
        val = float(num)
    except ValueError as e:
        raise AnsibleFilterError(f"jvm_filters: invalid numeric size '{v}'") from e
    factor = _FACTORS.get(unit)
    if factor is None:
        raise AnsibleFilterError(f"jvm_filters: unknown unit in '{v}'")
    return int(val * factor)

def _to_mb(v: str) -> int:
    return max(0, _to_bytes(v) // (1024 * 1024))

def _svc(app_id: str) -> str:
    return get_entity_name(app_id)

def _mem_limit_mb(apps: dict, app_id: str) -> int:
    svc = _svc(app_id)
    raw = get_app_conf(apps, app_id, f"docker.services.{svc}.mem_limit")
    mb = _to_mb(raw)
    if mb <= 0:
        raise AnsibleFilterError(f"jvm_filters: mem_limit for '{svc}' must be > 0 MB (got '{raw}')")
    return mb

def _mem_res_mb(apps: dict, app_id: str) -> int:
    svc = _svc(app_id)
    raw = get_app_conf(apps, app_id, f"docker.services.{svc}.mem_reservation")
    mb = _to_mb(raw)
    if mb <= 0:
        raise AnsibleFilterError(f"jvm_filters: mem_reservation for '{svc}' must be > 0 MB (got '{raw}')")
    return mb

def jvm_max_mb(apps: dict, app_id: str) -> int:
    """Xmx = min( floor(0.7*limit), limit-1024, 12288 ) with floor at 1024 MB."""
    limit_mb = _mem_limit_mb(apps, app_id)
    c1 = (limit_mb * 7) // 10
    c2 = max(0, limit_mb - 1024)
    c3 = 12288
    return max(1024, min(c1, c2, c3))

def jvm_min_mb(apps: dict, app_id: str) -> int:
    """Xms = min( floor(Xmx/2), mem_reservation, Xmx ) with floor at 512 MB."""
    xmx = jvm_max_mb(apps, app_id)
    res = _mem_res_mb(apps, app_id)
    return max(512, min(xmx // 2, res, xmx))

class FilterModule(object):
    def filters(self):
        return {
            "jvm_max_mb": jvm_max_mb,
            "jvm_min_mb": jvm_min_mb,
        }
