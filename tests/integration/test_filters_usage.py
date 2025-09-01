import ast
import os
import re
import unittest
from typing import Dict, List, Tuple, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

FILTER_PLUGIN_BASES = [
    os.path.join(PROJECT_ROOT, "filter_plugins"),
    os.path.join(PROJECT_ROOT, "roles"),
]

SEARCH_BASES = [PROJECT_ROOT]

SEARCH_EXTS = (".yml", ".yaml", ".j2", ".jinja2", ".tmpl", ".py")

def _iter_files(base: str, *, py_only: bool = False):
    for root, _, files in os.walk(base):
        for fn in files:
            if py_only and not fn.endswith(".py"):
                continue
            if not py_only and not fn.endswith(SEARCH_EXTS):
                continue
            yield os.path.join(root, fn)

def _is_filter_plugins_dir(path: str) -> bool:
    return "filter_plugins" in os.path.normpath(path).split(os.sep)

def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""

# ---------------------------
# Filter definition extraction
# ---------------------------

class _FiltersCollector(ast.NodeVisitor):
    """
    Extract mappings returned by FilterModule.filters().
    Handles:
      return {'name': fn, "x": y}
      d = {'name': fn}; d.update({...}); return d
      return dict(name=fn, x=y)
    """
    def __init__(self):
        self.defs: List[Tuple[str, str]] = []  # (filter_name, callable_name)

    def visit_Return(self, node: ast.Return):
        mapping = self._extract_mapping(node.value)
        for k, v in mapping:
            self.defs.append((k, v))

    def _extract_mapping(self, node) -> List[Tuple[str, str]]:
        pairs: List[Tuple[str, str]] = []

        # dict literal
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                key = k.value if isinstance(k, ast.Constant) and isinstance(k.value, str) else None
                val = self._name_of(v)
                if key:
                    pairs.append((key, val))
            return pairs

        # dict(...) call
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
            # keywords: dict(name=fn)
            for kw in node.keywords or []:
                if kw.arg:
                    pairs.append((kw.arg, self._name_of(kw.value)))
            return pairs

        # Name (variable) that might be a dict assembled earlier in the function
        if isinstance(node, ast.Name):
            # Fallback: we can't easily dataflow-resolve here; handled elsewhere by walking Assign/Call
            return []

        return []

    @staticmethod
    def _name_of(v) -> str:
        if isinstance(v, ast.Name):
            return v.id
        if isinstance(v, ast.Attribute):
            return v.attr  # take right-most name
        return ""

def _collect_filters_from_filters_method(func: ast.FunctionDef) -> List[Tuple[str, str]]:
    """
    Walks the function to assemble any mapping that flows into the return.
    We capture direct return dicts and also a common pattern:
        d = {...}
        d.update({...})
        return d
    """
    collector = _FiltersCollector()
    collector.visit(func)

    # additionally scan simple 'X = {...}' and 'X.update({...})' patterns,
    # and if 'return X' occurs, merge those dicts.
    name_dicts: Dict[str, List[Tuple[str, str]]] = {}
    returns: List[str] = []

    for n in ast.walk(func):
        if isinstance(n, ast.Assign):
            # X = { ... }
            if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                tgt = n.targets[0].id
                pairs = _FiltersCollector()._extract_mapping(n.value)
                if pairs:
                    name_dicts.setdefault(tgt, []).extend(pairs)
        elif isinstance(n, ast.Call):
            # X.update({ ... })
            if isinstance(n.func, ast.Attribute) and n.func.attr == "update":
                obj = n.func.value
                if isinstance(obj, ast.Name):
                    add_pairs = _FiltersCollector()._extract_mapping(n.args[0] if n.args else None)
                    if add_pairs:
                        name_dicts.setdefault(obj.id, []).extend(add_pairs)
        elif isinstance(n, ast.Return) and isinstance(n.value, ast.Name):
            returns.append(n.value.id)

    for rname in returns:
        for p in name_dicts.get(rname, []):
            collector.defs.append(p)

    # dedupe
    seen = set()
    out: List[Tuple[str, str]] = []
    for k, v in collector.defs:
        if (k, v) not in seen:
            seen.add((k, v))
            out.append((k, v))
    return out

def _ast_collect_filters_from_file(path: str) -> List[Tuple[str, str, str]]:
    code = _read(path)
    if not code:
        return []
    try:
        tree = ast.parse(code, filename=path)
    except Exception:
        return []

    results: List[Tuple[str, str, str]] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "FilterModule":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "filters":
                    for (fname, callname) in _collect_filters_from_filters_method(item):
                        results.append((fname, callname, path))
    return results

def collect_defined_filters() -> List[Dict[str, str]]:
    found: List[Dict[str, str]] = []
    for base in FILTER_PLUGIN_BASES:
        for path in _iter_files(base, py_only=True):
            if not _is_filter_plugins_dir(path):
                continue
            for (filter_name, callable_name, fpath) in _ast_collect_filters_from_file(path):
                found.append({"filter": filter_name, "callable": callable_name, "file": fpath})
    return found

# ---------------------------
# Usage detection
# ---------------------------

def _compile_jinja_patterns(name: str) -> list[re.Pattern]:
    """
    Build robust patterns that match Jinja filter usage without using '%' string formatting.
    Handles:
      - {{ ... | name }}
      - {% ... | name %}
      - {% filter name %}...{% endfilter %}
      - bare YAML/Jinja like: when: x | name
    """
    escaped = re.escape(name)
    return [
        re.compile(r"\{\{[^}]*\|\s*" + escaped + r"\b", re.DOTALL),   # {{ ... | name }}
        re.compile(r"\{%\s*[^%]*\|\s*" + escaped + r"\b", re.DOTALL), # {% ... | name %}
        re.compile(r"\{%\s*filter\s+" + escaped + r"\b"),             # {% filter name %}
        re.compile(r"\|\s*" + escaped + r"\b"),                       # bare: when: x | name
    ]

def _python_call_pattern(callable_name: str) -> Optional[re.Pattern]:
    if not callable_name:
        return None
    return re.compile(r"\b%s\s*\(" % re.escape(callable_name))

def search_usage(filter_name: str, callable_name: str, *, skip_file: str) -> tuple[bool, bool]:
    """
    Search for filter usage.

    Returns tuple:
      (used_anywhere, used_outside_tests)

    - used_anywhere: True if found in repo at all
    - used_outside_tests: True if found outside tests/
    """
    jinja_pats = _compile_jinja_patterns(filter_name)
    py_pat = _python_call_pattern(callable_name)

    used_anywhere = False
    used_outside_tests = False

    for base in SEARCH_BASES:
        for path in _iter_files(base, py_only=False):
            try:
                if os.path.samefile(path, skip_file):
                    continue
            except Exception:
                pass

            content = _read(path)
            if not content:
                continue

            hit = False
            for pat in jinja_pats:
                if pat.search(content):
                    hit = True
                    break

            if not hit and py_pat and path.endswith(".py") and py_pat.search(content):
                hit = True

            if hit:
                used_anywhere = True
                if "/tests/" not in path and not path.endswith("tests"):
                    used_outside_tests = True

    return used_anywhere, used_outside_tests

class TestFilterDefinitionsAreUsed(unittest.TestCase):
    def test_every_defined_filter_is_used(self):
        definitions = collect_defined_filters()
        if not definitions:
            self.skipTest("No filters found under filter_plugins/.")

        unused = []
        for d in definitions:
            f_name, c_name, f_path = d["filter"], d["callable"], d["file"]
            used_any, used_outside = search_usage(f_name, c_name, skip_file=f_path)
            if not used_any:
                unused.append((f_name, c_name, f_path, "not used anywhere"))
            elif not used_outside:
                unused.append((f_name, c_name, f_path, "only used in tests"))

        if unused:
            msg = ["The following filters are invalidly unused:"]
            for f, c, p, reason in sorted(unused):
                msg.append(f"- '{f}' (callable '{c or 'unknown'}') defined in {p} → {reason}")
            self.fail("\n".join(msg))

if __name__ == "__main__":
    unittest.main()
