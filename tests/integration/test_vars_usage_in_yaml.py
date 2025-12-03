import unittest
from pathlib import Path
import re
from typing import Any, Iterable, Set, List
import yaml


class TestVarsPassedAreUsed(unittest.TestCase):
    """
    Integration test:
    - Walk all *.yml/*.yaml and *.j2 files
    - Collect variable names passed via task-level `vars:`
    - Consider a var "used" if it appears in ANY of:
        • Jinja output blocks:     {{ ... var_name ... }}
        • Jinja statement blocks:  {% ... var_name ... %}
          (robust against inner '}' / '%' via tempered regex)
        • Ansible expressions in YAML:
            - when: <expr>          (string or list of strings)
            - loop: <expr>
            - with_*: <expr>

    Additional rule:
    - Do NOT count as used if the token is immediately followed by '(' (optionally with whitespace),
      i.e. treat `var_name(` as a function/macro call, not a variable usage.
    """

    REPO_ROOT = Path(__file__).resolve().parents[2]
    YAML_EXTENSIONS = {".yml", ".yaml"}
    JINJA_EXTENSIONS = {".j2"}

    # ---------- File iteration & YAML loading ----------

    def _iter_files(self, extensions: set[str]) -> Iterable[Path]:
        for p in self.REPO_ROOT.rglob("*"):
            if p.is_file() and p.suffix in extensions:
                yield p

    def _load_yaml_documents(self, path: Path) -> List[Any]:
        try:
            with path.open("r", encoding="utf-8") as f:
                return list(yaml.safe_load_all(f)) or []
        except Exception:
            # File may contain heavy templating or anchors; skip structural parse
            return []

    def _walk_mapping(self, node: Any) -> Iterable[dict]:
        if isinstance(node, dict):
            yield node
            for v in node.values():
                yield from self._walk_mapping(v)
        elif isinstance(node, list):
            for item in node:
                yield from self._walk_mapping(item)

    # ---------- Collect vars passed via `vars:` ----------

    def _collect_vars_passed(self) -> Set[str]:
        collected: Set[str] = set()
        for yml in self._iter_files(self.YAML_EXTENSIONS):
            docs = self._load_yaml_documents(yml)
            for doc in docs:
                for mapping in self._walk_mapping(doc):
                    if "vars" in mapping and isinstance(mapping["vars"], dict):
                        for k in mapping["vars"].keys():
                            if isinstance(k, str) and k.strip():
                                collected.add(k.strip())
        return collected

    # ---------- Gather text for Jinja usage scanning ----------

    def _concat_texts(self) -> str:
        parts: List[str] = []
        for f in self._iter_files(self.YAML_EXTENSIONS | self.JINJA_EXTENSIONS):
            try:
                parts.append(f.read_text(encoding="utf-8"))
            except Exception:
                # Non-UTF8 or unreadable — ignore
                pass
        return "\n".join(parts)

    # ---------- Extract Ansible expression strings from YAML ----------

    def _collect_ansible_expressions(self) -> List[str]:
        """
        Return a flat list of strings taken from Ansible expression-bearing fields:
        - when: <str> or when: [<str>, <str>, ...]
        - loop: <str>
        - with_*: <str>
        """
        exprs: List[str] = []
        for yml in self._iter_files(self.YAML_EXTENSIONS):
            docs = self._load_yaml_documents(yml)
            for doc in docs:
                for mapping in self._walk_mapping(doc):
                    for key, val in list(mapping.items()):
                        if key == "when":
                            if isinstance(val, str):
                                exprs.append(val)
                            elif isinstance(val, list):
                                exprs.extend([x for x in val if isinstance(x, str)])
                        elif key == "loop":
                            if isinstance(val, str):
                                exprs.append(val)
                        elif isinstance(key, str) and key.startswith("with_"):
                            if isinstance(val, str):
                                exprs.append(val)
        return exprs

    # ---------- Usage checks ----------

    def _used_in_jinja_blocks(self, var_name: str, text: str) -> bool:
        """
        Detect var usage inside Jinja blocks, excluding function/macro calls like `var_name(...)`.
        We use a tempered regex to avoid stopping at the first '}}'/'%}' and a negative lookahead
        `(?!\\s*\\()` after the token.
        """
        # Word token not followed by '(' → real variable usage
        token = r"\b" + re.escape(var_name) + r"\b(?!\s*\()"

        # Output blocks: {{ ... }}
        pat_output = re.compile(
            r"{{(?:(?!}}).)*" + token + r"(?:(?!}}).)*}}",
            re.DOTALL,
        )
        # Statement blocks: {% ... %}
        pat_stmt = re.compile(
            r"{%(?:(?!%}).)*" + token + r"(?:(?!%}).)*%}",
            re.DOTALL,
        )
        return pat_output.search(text) is not None or pat_stmt.search(text) is not None

    def _used_in_ansible_exprs(self, var_name: str, exprs: List[str]) -> bool:
        """
        Detect var usage in Ansible expressions (when/loop/with_*),
        excluding function/macro calls like `var_name(...)`.
        """
        pat = re.compile(r"\b" + re.escape(var_name) + r"\b(?!\s*\()")
        return any(pat.search(e) for e in exprs)

    # ---------- Test ----------

    def test_vars_passed_are_used_in_yaml_or_jinja(self):
        vars_passed = self._collect_vars_passed()
        self.assertTrue(
            vars_passed,
            "No variables passed via `vars:` were found. "
            "Check the repo root path in this test."
        )

        all_text = self._concat_texts()
        ansible_exprs = self._collect_ansible_expressions()

        unused: List[str] = []
        for var_name in sorted(vars_passed):
            used = (
                self._used_in_jinja_blocks(var_name, all_text)
                or self._used_in_ansible_exprs(var_name, ansible_exprs)
            )
            if not used:
                if var_name not in ['ansible_python_interpreter']:
                    unused.append(var_name)

        if unused:
            msg = (
                "The following variables are passed via `vars:` but never referenced in:\n"
                "  • Jinja output/statement blocks ({{ ... }} / {% ... %}) OR\n"
                "  • Ansible expressions (when/loop/with_*)\n\n"
                + "\n".join(f"  - {v}" for v in unused)
                + "\n\nNotes:\n"
                  " • Function-like tokens (name followed by '(') are ignored intentionally.\n"
                  " • If a var is only used in Python code or other file types, extend the test accordingly\n"
                  "   or remove the var if it's truly unused."
            )
            self.fail(msg)
