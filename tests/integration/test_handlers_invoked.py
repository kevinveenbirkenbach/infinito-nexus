import os
import glob
import re
import unittest
import yaml
from typing import Any, Dict, Iterable, List, Set


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
        # If this dict looks like a task (has common task keys), yield it.
        # We are liberal and treat any dict as a potential task entry.
        yield node
        # Recurse into any list-of-dicts values (blocks, etc.)
        for v in node.values():
            if isinstance(v, list):
                if any(isinstance(x, dict) for x in v):
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

def _expand_dynamic_notify(value: str) -> List[str]:
    """
    If 'value' is a Jinja expression like:
        "{{ 'reload system daemon' if cond else 'refresh systemctl service' }}"
    then extract all quoted literals as potential targets.
    Always include the raw value too (just in case it is a plain name).
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


def collect_notify_calls_from_tasks(task_file: str) -> Set[str]:
    """
    From a task file, collect all notification targets via:
      - 'notify:' (string or list), including dynamic Jinja expressions with literals,
      - any occurrence of 'package_notify:' (string or list), anywhere in the task dict.
    Also traverses tasks nested inside 'block', 'rescue', 'always', etc.
    """
    notified: Set[str] = set()
    docs = load_yaml_documents(task_file)

    for entry in iter_task_like_entries(docs):
        # Standard notify:
        if "notify" in entry:
            for item in as_str_list(entry["notify"]):
                for expanded in _expand_dynamic_notify(item):
                    expanded = expanded.strip()
                    if expanded:
                        notified.add(expanded)

        # package_notify anywhere in the task (top-level or nested)
        def walk_for_package_notify(node: Any):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "package_notify":
                        for item in as_str_list(v):
                            for expanded in _expand_dynamic_notify(item):
                                expanded = expanded.strip()
                                if expanded:
                                    notified.add(expanded)
                    else:
                        walk_for_package_notify(v)
            elif isinstance(node, list):
                for v in node:
                    walk_for_package_notify(v)

        walk_for_package_notify(entry)

    return notified


# ---------- Test case ----------

class TestHandlersInvoked(unittest.TestCase):
    """
    Ensures that every handler defined in roles/*/handlers/*.yml(.yaml)
    is referenced at least once via either:
      - tasks' 'notify:' fields (supports Jinja conditionals with quoted literals), or
      - any 'package_notify:' usage (e.g., include_role: vars: package_notify: "...").

    A handler is considered covered if ANY of its {name + listen} aliases is notified.
    """

    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        self.roles_dir = os.path.join(repo_root, "roles")

        # Handlers: support .yml and .yaml
        self.handler_files = (
            glob.glob(os.path.join(self.roles_dir, "*/handlers/*.yml"))
            + glob.glob(os.path.join(self.roles_dir, "*/handlers/*.yaml"))
        )

        # Tasks: recurse under tasks for both .yml and .yaml
        self.task_files = (
            glob.glob(os.path.join(self.roles_dir, "*", "tasks", "**", "*.yml"), recursive=True)
            + glob.glob(os.path.join(self.roles_dir, "*", "tasks", "**", "*.yaml"), recursive=True)
        )

    def test_all_handlers_have_a_notifier(self):
        # 1) Collect handler groups (name + listen) for each handler task
        handler_groups: List[Set[str]] = []
        for hf in self.handler_files:
            handler_groups.extend(collect_handler_groups(hf))

        # 2) Collect all notified targets (notify + package_notify) from tasks
        all_notified: Set[str] = set()
        for tf in self.task_files:
            all_notified |= collect_notify_calls_from_tasks(tf)

        # 3) A handler group is covered if any alias is notified
        missing_groups: List[Set[str]] = [grp for grp in handler_groups if not (grp & all_notified)]

        if missing_groups:
            representatives: List[str] = []
            for grp in missing_groups:
                representatives.append(sorted(grp)[0])
            representatives = sorted(set(representatives))

            msg = [
                "The following handlers are defined but never notified (via 'notify:' or 'package_notify:'):",
                *[f"  - {m}" for m in representatives],
                "",
                "Note:",
                "  • A handler is considered covered if *any* of its {name + listen} aliases is notified.",
                "  • Dynamic Jinja notify expressions are supported by extracting quoted literals.",
                "  • Ensure 'notify:' uses the exact handler name or one of its 'listen' aliases.",
                "  • If you trigger builds via roles/vars, set 'package_notify:' to the handler name.",
            ]
            self.fail("\n".join(msg))


if __name__ == "__main__":
    unittest.main()
