import os
import glob
import re
import unittest
import yaml
from typing import Any, Dict, Iterable, List, Set, Tuple, Optional


# ---------- YAML helpers ----------


def load_yaml_documents(path: str) -> List[Any]:
    """
    Load one or more YAML documents from a file and return them as a list.
    Raises AssertionError with a helpful message on parse errors.
    """
    with open(path, "r", encoding="utf-8") as f:
        try:
            docs = list(yaml.safe_load_all(f))
            return [d for d in docs if d is not None]
        except yaml.YAMLError as e:
            raise AssertionError(f"YAML parsing error in {path}: {e}")


def _iter_task_like_entries(node: Any) -> Iterable[Dict[str, Any]]:
    """
    Recursively yield task/handler-like dict entries from a YAML node.
    Handles top-level lists and dict-wrapped lists, and also drills into
    Ansible blocks ('block', 'rescue', 'always') or any list of dicts.
    """
    if isinstance(node, list):
        for item in node:
            yield from _iter_task_like_entries(item)
    elif isinstance(node, dict):
        # Consider any dict as a potential task/handler entry.
        yield node
        # Recurse into list-of-dicts values (blocks, etc.)
        for v in node.values():
            if isinstance(v, list) and any(isinstance(x, dict) for x in v):
                yield from _iter_task_like_entries(v)


def iter_task_like_entries(docs: List[Any]) -> Iterable[Dict[str, Any]]:
    for doc in docs:
        yield from _iter_task_like_entries(doc)


def as_str_list(val: Any) -> List[str]:
    """Normalize a YAML value (string or list) into a list of strings."""
    if val is None:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        return [str(v) for v in val]
    return [str(val)]


# ---------- Notify extraction helpers ----------

# Extract quoted literals inside a string (e.g. from Jinja conditionals)
_QUOTED_RE = re.compile(r"""(['"])(.+?)\1""")

def _jinja_mixed_to_regex(value: str) -> Optional[re.Pattern]:
    """
    Turn a string that mixes plain text with Jinja placeholders into a ^...$ regex.
    Example: 'Import {{ folder }} LDIF files' -> r'^Import .+ LDIF files$'
    Returns None if there is no Jinja placeholder.
    """
    s = value.strip()
    if "{{" not in s or "}}" not in s:
        return None
    parts = re.split(r"(\{\{.*?\}\})", s)
    regex_str = (
        "^"
        + "".join(
            (".+" if p.startswith("{{") and p.endswith("}}") else re.escape(p))
            for p in parts
        )
        + "$"
    )
    return re.compile(regex_str)


def _expand_dynamic_notify(value: str) -> List[str]:
    """
    If 'value' is a Jinja expression like:
        "{{ 'reload system daemon' if cond else 'refresh systemctl service' }}"
    then extract all quoted literals as potential targets.
    Always include the raw value too (in case it is already a plain name).
    """
    results = []
    s = value.strip()
    if s:
        results.append(s)
    if "{{" in s and "}}" in s:
        for m in _QUOTED_RE.finditer(s):
            literal = m.group(2).strip()
            if literal:
                results.append(literal)
    return results


# ---------- Extraction from handlers/tasks ----------


def collect_handler_groups(handler_file: str) -> List[Set[str]]:
    """
    Build groups of acceptable targets for each handler task from a handlers file.
    For each handler, collect its 'name' and all 'listen' aliases.
    A handler is considered covered if ANY alias in its group is notified.
    """
    groups: List[Set[str]] = []
    docs = load_yaml_documents(handler_file)

    for entry in iter_task_like_entries(docs):
        names: Set[str] = set()

        # primary name
        if isinstance(entry.get("name"), str):
            nm = entry["name"].strip()
            if nm:
                names.add(nm)

        # listen aliases (string or list)
        if "listen" in entry:
            for item in as_str_list(entry["listen"]):
                item = item.strip()
                if item:
                    names.add(item)

        if names:
            groups.append(names)

    return groups


def collect_notify_calls_from_tasks(
    task_file: str,
) -> Tuple[Set[str], List[re.Pattern]]:
    """
    From a task file, collect all notification targets via:
      - 'notify:' (string or list), including dynamic Jinja expressions with literals,
      - any occurrence of 'package_notify:' (string or list), anywhere in the task dict.
    Also traverses tasks nested inside 'block', 'rescue', 'always', etc.

    Returns:
      (exact_names, regex_patterns)
    """
    notified_exact: Set[str] = set()
    notified_patterns: List[re.Pattern] = []
    docs = load_yaml_documents(task_file)

    for entry in iter_task_like_entries(docs):
        # Standard notify:
        if "notify" in entry:
            for item in as_str_list(entry["notify"]):
                item_str = item.strip()

                # Case 1: whole string is just a Jinja expression -> ignore
                if item_str.startswith("{{") and item_str.endswith("}}"):
                    continue

                has_jinja = "{{" in item_str and "}}" in item_str

                # Case 2: expand quoted literals inside Jinja expressions (as exacts)
                if has_jinja:
                    # Only take the quoted literals; do NOT add the raw mixed string as exact.
                    for m in _QUOTED_RE.finditer(item_str):
                        lit = m.group(2).strip()
                        if lit:
                            notified_exact.add(lit)
                else:
                    # No Jinja -> the whole string is an exact name.
                    notified_exact.add(item_str)

                # Case 3: mixed string with Jinja placeholder -> treat as regex
                rx = _jinja_mixed_to_regex(item_str)
                if rx is not None:
                    notified_patterns.append(rx)

        # package_notify anywhere in the task (top-level or nested)
        def walk_for_package_notify(node: Any):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "package_notify":
                        for item in as_str_list(v):
                            item_str = item.strip()

                            # Ignore pure Jinja
                            if item_str.startswith("{{") and item_str.endswith("}}"):
                                continue

                            has_jinja = "{{" in item_str and "}}" in item_str

                            if has_jinja:
                                # Only quoted literals as exacts
                                for m in _QUOTED_RE.finditer(item_str):
                                    lit = m.group(2).strip()
                                    if lit:
                                        notified_exact.add(lit)
                            else:
                                notified_exact.add(item_str)

                            # mixed -> regex
                            rx = _jinja_mixed_to_regex(item_str)
                            if rx is not None:
                                notified_patterns.append(rx)
                    else:
                        walk_for_package_notify(v)
            elif isinstance(node, list):
                for v in node:
                    walk_for_package_notify(v)

        walk_for_package_notify(entry)

    return notified_exact, notified_patterns


# ---------- Test case ----------


class TestHandlersInvoked(unittest.TestCase):
    """
    Ensures:
      (A) Every handler defined in roles/*/handlers/*.yml(.yaml) is referenced at least once
          via tasks' 'notify:' or any 'package_notify:' (exact or regex match from Jinja-mixed strings).
      (B) Every notified target in tasks points to an existing handler alias (name or listen).
    """

    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        self.roles_dir = os.path.join(repo_root, "roles")

        # Handlers: support .yml and .yaml
        self.handler_files = glob.glob(
            os.path.join(self.roles_dir, "*/handlers/*.yml")
        ) + glob.glob(os.path.join(self.roles_dir, "*/handlers/*.yaml"))

        # Tasks: recurse under tasks for both .yml and .yaml
        self.task_files = glob.glob(
            os.path.join(self.roles_dir, "*", "tasks", "**", "*.yml"), recursive=True
        ) + glob.glob(
            os.path.join(self.roles_dir, "*", "tasks", "**", "*.yaml"), recursive=True
        )

    def test_all_handlers_have_a_notifier_and_all_notifies_have_a_handler(self):
        # 1) Collect handler groups (name + listen) for each handler task
        handler_groups: List[Set[str]] = []
        for hf in self.handler_files:
            handler_groups.extend(collect_handler_groups(hf))

        # Flatten all handler aliases for reverse checks
        all_aliases: Set[str] = (
            set().union(*handler_groups) if handler_groups else set()
        )

        # 2) Collect all notified targets (notify + package_notify) from tasks
        notified_exact: Set[str] = set()
        notified_patterns: List[re.Pattern] = []
        for tf in self.task_files:
            ex, pats = collect_notify_calls_from_tasks(tf)
            notified_exact |= ex
            notified_patterns.extend(pats)

        def group_is_covered(grp: Set[str]) -> bool:
            # exact hit?
            if grp & notified_exact:
                return True
            # regex hit?
            for alias in grp:
                for rx in notified_patterns:
                    if rx.match(alias):
                        return True
            return False

        # 3A) Every handler group is covered if any alias is notified (exact or regex)
        missing_groups: List[Set[str]] = [
            grp for grp in handler_groups if not group_is_covered(grp)
        ]

        if missing_groups:
            representatives: List[str] = []
            for grp in missing_groups:
                representatives.append(sorted(grp)[0])
            representatives = sorted(set(representatives))

            msg = [
                "The following handlers are defined but never notified (via 'notify:' or 'package_notify:'):",
                *[f"  - {m}" for m in representatives],
                "",
                "Notes:",
                "  • A handler is considered covered if *any* of its {name + listen} aliases is notified.",
                "  • We support dynamic Jinja notify expressions by extracting quoted literals",
                "    and by interpreting mixed strings with Jinja placeholders as wildcard regex.",
                "  • Ensure 'notify:' uses the exact handler name, one of its 'listen' aliases,",
                "    or a compatible wildcard string that matches the handler via regex.",
                "  • If you trigger builds via roles/vars, set 'package_notify:' to the handler name.",
            ]
            self.fail("\n".join(msg))

        # 3B) Reverse validation:
        #     Every notified target must resolve to an existing handler alias.
        #     - Exact notified strings must match an alias exactly.
        #     - Jinja-mixed strings (patterns) must match at least one alias via regex.
        missing_exacts = sorted([s for s in notified_exact if s not in all_aliases])

        orphan_patterns = sorted(
            {
                rx.pattern
                for rx in notified_patterns
                if not any(rx.match(alias) for alias in all_aliases)
            }
        )

        if missing_exacts or orphan_patterns:
            msg = ["Some notify targets do not map to any existing handler:"]
            if missing_exacts:
                msg.append("  • Missing exact handler aliases:")
                msg.extend([f"    - {s}" for s in missing_exacts])
            if orphan_patterns:
                msg.append(
                    "  • Pattern notifications with no matching handler alias (regex):"
                )
                msg.extend([f"    - {pat}" for pat in orphan_patterns])
            msg += [
                "",
                "Hints:",
                "  - Make sure a handler with matching 'name' or 'listen' exists.",
                "  - Pure Jinja expressions like '{{ some_var }}' are ignored in this check.",
                "  - Mixed strings like 'Import {{ folder }} LDIF files' are treated as regex (e.g., '^Import .+ LDIF files$').",
                "  - Consider adding a 'listen:' alias to the handler if you want to keep a flexible notify pattern.",
            ]
            self.fail("\n".join(msg))


if __name__ == "__main__":
    unittest.main()
