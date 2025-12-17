import re
import time
from typing import Any, Dict, Union, List, Set

class DictRenderer:
    """
    Resolves placeholders in the form << path >> within nested dictionaries,
    supporting hyphens, numeric list indexing, and quoted keys via ['key'] or ["key"].
    """
    # Match << path >> where path contains no whitespace or closing >
    PATTERN = re.compile(r"<<\s*(?P<path>[^\s>]+)\s*>>")
    # Tokenizes a path into unquoted keys, single-quoted, double-quoted keys, or numeric indices
    TOKEN_REGEX = re.compile(
        r"(?P<key>[\w\-]+)"
        r"|\['(?P<qkey>[^']+)'\]"
        r"|\[\"(?P<dkey>[^\"]+)\"\]"
        r"|\[(?P<idx>\d+)\]"
    )

    def __init__(self, verbose: bool = False, timeout: float = 10.0):
        self.verbose = verbose
        self.timeout = timeout

    def render(self, data: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
        start = time.monotonic()
        self.root = data
        rendered = data
        pass_num = 0

        while True:
            pass_num += 1
            if self.verbose:
                print(f"[DictRenderer] Pass {pass_num} starting...")
            rendered, changed = self._render_pass(rendered)
            if not changed:
                if self.verbose:
                    print(f"[DictRenderer] No more placeholders after pass {pass_num}.")
                break
            if time.monotonic() - start > self.timeout:
                raise TimeoutError(f"Rendering exceeded timeout of {self.timeout} seconds")

        # After all passes, raise error on unresolved placeholders
        unresolved = self.find_unresolved(rendered)
        if unresolved:
            raise ValueError(f"Unresolved placeholders: {', '.join(sorted(unresolved))}")

        return rendered

    def _render_pass(self, obj: Any) -> (Any, bool):
        if isinstance(obj, dict):
            new = {}
            changed = False
            for k, v in obj.items():
                nv, ch = self._render_pass(v)
                new[k] = nv
                changed = changed or ch
            return new, changed
        if isinstance(obj, list):
            new_list = []
            changed = False
            for item in obj:
                ni, ch = self._render_pass(item)
                new_list.append(ni)
                changed = changed or ch
            return new_list, changed
        if isinstance(obj, str):
            def repl(m):
                path = m.group('path')
                val = self._lookup(path)
                if val is not None:
                    if self.verbose:
                        print(f"[DictRenderer] Resolving <<{path}>> -> {val}")
                    return str(val)
                return m.group(0)
            new_str = self.PATTERN.sub(repl, obj)
            return new_str, new_str != obj
        return obj, False

    def _lookup(self, path: str) -> Any:
        current = self.root
        for m in self.TOKEN_REGEX.finditer(path):
            if m.group('key') is not None:
                if isinstance(current, dict):
                    current = current.get(m.group('key'))
                else:
                    return None
            elif m.group('qkey') is not None:
                if isinstance(current, dict):
                    current = current.get(m.group('qkey'))
                else:
                    return None
            elif m.group('dkey') is not None:
                if isinstance(current, dict):
                    current = current.get(m.group('dkey'))
                else:
                    return None
            elif m.group('idx') is not None:
                idx = int(m.group('idx'))
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            if current is None:
                return None
        return current

    def find_unresolved(self, data: Any) -> Set[str]:
        """Return all paths of unresolved << placeholders in data."""
        unresolved: Set[str] = set()
        if isinstance(data, dict):
            for v in data.values():
                unresolved |= self.find_unresolved(v)
        elif isinstance(data, list):
            for item in data:
                unresolved |= self.find_unresolved(item)
        elif isinstance(data, str):
            for m in self.PATTERN.finditer(data):
                unresolved.add(m.group('path'))
        return unresolved
