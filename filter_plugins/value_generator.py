# filter_plugins/value_generator.py

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys
from typing import Type


@lru_cache(maxsize=1)
def _value_generator_cls() -> Type[object]:
    """
    Load ValueGenerator from module_utils/manager/value_generator.py.

    Assumptions:
    - module_utils/manager/__init__.py exists (package import works)
    - filter_plugins/ is located at repo root (or adjust parents[1])
    """
    repo_root = Path(__file__).resolve().parents[1]
    module_utils_path = repo_root / "module_utils"

    if not module_utils_path.is_dir():
        raise RuntimeError(f"module_utils directory not found at: {module_utils_path}")

    if str(module_utils_path) not in sys.path:
        sys.path.insert(0, str(module_utils_path))

    # module_utils/manager/value_generator.py => manager.value_generator
    from manager.value_generator import ValueGenerator  # type: ignore

    return ValueGenerator


def strong_password(length: int = 32) -> str:
    ValueGenerator = _value_generator_cls()
    return ValueGenerator().generate_strong_password(int(length))


class FilterModule:
    def filters(self):
        return {
            "strong_password": strong_password,
        }
