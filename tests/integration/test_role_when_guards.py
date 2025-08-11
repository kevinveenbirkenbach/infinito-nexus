import os
import glob
import unittest
from typing import Any, Dict, List, Tuple, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    raise SystemExit("Please `pip install pyyaml` to run this test.")


# ---------- Helpers: repo + YAML parsing ----------

def _find_repo_root_containing(relative: str, max_depth: int = 8) -> str:
    """Walk upwards from this file to find the repo root that contains `relative`."""
    here = os.path.abspath(os.path.dirname(__file__))
    cur = here
    for _ in range(max_depth):
        candidate = os.path.join(cur, relative)
        if os.path.exists(candidate):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    raise FileNotFoundError(f"Could not find {relative!r} upwards from {here}")


def _load_yaml_file(path: str) -> List[Dict[str, Any]]:
    """
    Load a tasks YAML file.
    Returns a list of top-level task dicts. If the file is empty, returns [].
    Supports multi-doc YAML.
    """
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    docs = list(yaml.safe_load_all(content)) or []
    tasks: List[Dict[str, Any]] = []
    for doc in docs:
        if doc is None:
            continue
        if isinstance(doc, list):
            tasks.extend([t for t in doc if isinstance(t, dict)])
        elif isinstance(doc, dict):
            if "tasks" in doc and isinstance(doc["tasks"], list):
                tasks.extend([t for t in doc["tasks"] if isinstance(t, dict)])
            else:
                tasks.append(doc)
    return tasks


# ---------- Helpers: when / structure checks ----------

def _normalize_when(value: Any) -> List[str]:
    """
    Normalize a 'when' value (string | list | bool | None) to a list of strings.
    Non-string entries are ignored.
    """
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, str):
        v = value.strip()
        return [v] if v else []
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    out.append(s)
        return out
    return []


def _task_has_block_with_when(task: Dict[str, Any]) -> bool:
    return "block" in task and bool(_normalize_when(task.get("when")))


def _is_pure_guarded_tasks_file(tasks: List[Dict[str, Any]]) -> Tuple[List[str], bool]:
    """
    A "pure guarded" tasks file has EXACTLY ONE top-level task,
    that task contains a 'block', and that task has a 'when' condition.
    Returns (guard_conditions, is_pure_guarded).
    """
    if len(tasks) != 1:
        return [], False
    only_task = tasks[0]
    if not _task_has_block_with_when(only_task):
        return [], False
    return _normalize_when(only_task.get("when")), True


# ---------- Helpers: discovery ----------

def _iter_all_tasks_files(repo_root: str) -> List[str]:
    """
    Return all tasks/*.yml|*.yaml files in the project (recursively).
    """
    patterns = [
        os.path.join(repo_root, "**", "tasks", "*.yml"),
        os.path.join(repo_root, "**", "tasks", "*.yaml"),
    ]
    files: List[str] = []
    for pat in patterns:
        files.extend(glob.glob(pat, recursive=True))
    # Deduplicate while keeping order
    seen = set()
    ordered: List[str] = []
    for p in files:
        if p not in seen:
            ordered.append(p)
            seen.add(p)
    return ordered


def _get_include_role_name(task: Dict[str, Any]) -> Optional[str]:
    """
    If task is an include_role task, return the role 'name'.
    Supports 'include_role' and 'ansible.builtin.include_role'.
    """
    for key in ("include_role", "ansible.builtin.include_role"):
        if key in task and isinstance(task[key], dict):
            role_name = task[key].get("name")
            if isinstance(role_name, str) and role_name.strip():
                return role_name.strip()
    return None


def _get_include_tasks_target(task: Dict[str, Any]) -> Optional[str]:
    """
    If task is an include_tasks, return the path string as-is (could be relative).
    Supports 'include_tasks' and 'ansible.builtin.include_tasks'.
    Returns None if not found or not a string.
    """
    for key in ("include_tasks", "ansible.builtin.include_tasks"):
        if key in task:
            val = task[key]
            if isinstance(val, str):
                return val.strip()
    return None


def _contains_jinja(s: str) -> bool:
    return "{{" in s or "{%" in s or "}}" in s or "%}" in s


def _resolve_include_tasks_path(include_value: str, including_file: str) -> Optional[str]:
    """
    Resolve an include_tasks path relative to the including file.
    If it contains Jinja or does not resolve to an existing file, return None.
    Tries exact path, then adds .yml / .yaml if extension missing.
    """
    if _contains_jinja(include_value):
        return None

    # Absolute path?
    candidates: List[str] = []
    if os.path.isabs(include_value):
        candidates.append(include_value)
    else:
        base = os.path.dirname(including_file)
        candidates.append(os.path.join(base, include_value))

    final_candidates: List[str] = []
    for c in candidates:
        final_candidates.append(c)
        root, ext = os.path.splitext(c)
        if ext == "":
            final_candidates.append(root + ".yml")
            final_candidates.append(root + ".yaml")

    for c in final_candidates:
        if os.path.isfile(c):
            return c

    return None


class PureGuardedIncludeTest(unittest.TestCase):
    """
    Enforce short-circuit includes ONLY for "pure guarded" targets:
      - Exactly one top-level task
      - That task is a 'block'
      - That task has a 'when'
    Apply to both:
      - include_role (roles/<role>/tasks/main.yml must be pure guarded)
      - include_tasks (target tasks file must be pure guarded)
    """

    @classmethod
    def setUpClass(cls):
        cls.repo_root = _find_repo_root_containing("roles")

        # Map pure guarded roles: role_name -> (guards, main_path)
        cls.pure_guarded_roles: Dict[str, Tuple[List[str], str]] = {}

        role_main_glob = os.path.join(cls.repo_root, "roles", "*", "tasks", "main.yml")
        for main_path in glob.glob(role_main_glob):
            role_name = os.path.basename(os.path.dirname(os.path.dirname(main_path)))  # roles/<role>/tasks/main.yml
            try:
                tasks = _load_yaml_file(main_path)
                guards, pure = _is_pure_guarded_tasks_file(tasks)
                if pure and guards:
                    cls.pure_guarded_roles[role_name] = (guards, main_path)
            except Exception:
                # If parsing fails, ignore here; will be caught when scanning all files if relevant
                pass

        # Cache of parsed tasks files for include_tasks: path -> (guards, pure)
        cls.tasks_file_cache: Dict[str, Tuple[List[str], bool]] = {}

        # All tasks files across repo
        cls.all_tasks_files = _iter_all_tasks_files(cls.repo_root)

    # ---------- Tests ----------

    def test_include_role_short_circuits_when_target_is_pure_guarded(self):
        failures: List[str] = []

        if not self.pure_guarded_roles:
            self.skipTest("No pure guarded roles found; nothing to validate for include_role.")

        for path in self.all_tasks_files:
            try:
                tasks = _load_yaml_file(path)
            except Exception as e:
                failures.append(f"[PARSE ERROR] {path}: {e}")
                continue

            for idx, task in enumerate(tasks):
                role_name = _get_include_role_name(task)
                if not role_name:
                    continue

                # Only enforce when the included role is pure guarded
                role_entry = self.pure_guarded_roles.get(role_name)
                if not role_entry:
                    continue

                guards, main_path = role_entry
                include_when = _normalize_when(task.get("when"))

                if not include_when:
                    failures.append(
                        f"{path} (task #{idx+1}) includes role '{role_name}' "
                        f"but lacks a 'when'. The role is pure guarded by {guards} in {main_path}. "
                        f"Add at least one of those guard expressions to the include to avoid loading the role unnecessarily."
                    )
                    continue

                if not any(req in include_when for req in guards):
                    failures.append(
                        f"{path} (task #{idx+1}) includes role '{role_name}' but its 'when' "
                        f"does not contain the role's guard.\n"
                        f"Role guard(s) from {main_path}: {guards}\n"
                        f"Include 'when': {include_when}\n"
                        "Add the role's guard condition to short-circuit when false."
                    )

        if failures:
            self.fail("Some include_role calls are missing pure-guard short-circuiting:\n\n" + "\n\n".join(failures))

    def test_include_tasks_short_circuits_when_target_is_pure_guarded(self):
        failures: List[str] = []

        for including_path in self.all_tasks_files:
            try:
                including_tasks = _load_yaml_file(including_path)
            except Exception as e:
                failures.append(f"[PARSE ERROR] {including_path}: {e}")
                continue

            for idx, task in enumerate(including_tasks):
                include_value = _get_include_tasks_target(task)
                if not include_value:
                    continue

                resolved = _resolve_include_tasks_path(include_value, including_path)
                if not resolved:
                    # Could not resolve (Jinja path or file not found). Skip enforcing.
                    continue

                # Load/inspect included tasks file (with cache)
                if resolved not in self.tasks_file_cache:
                    try:
                        target_tasks = _load_yaml_file(resolved)
                        guards, pure = _is_pure_guarded_tasks_file(target_tasks)
                        self.tasks_file_cache[resolved] = (guards, pure)
                    except Exception as e:
                        failures.append(f"[PARSE ERROR] included by {including_path} (task #{idx+1}): {resolved}: {e}")
                        # mark as non-pure to avoid repeated parsing attempts
                        self.tasks_file_cache[resolved] = ([], False)

                guards, pure = self.tasks_file_cache.get(resolved, ([], False))
                if not (pure and guards):
                    # Only enforce for pure guarded task files
                    continue

                include_when = _normalize_when(task.get("when"))

                if not include_when:
                    failures.append(
                        f"{including_path} (task #{idx+1}) includes tasks '{include_value}' "
                        f"-> {resolved}, which is PURE GUARDED by {guards}. "
                        f"Add at least one of those guard expressions to the include to avoid loading the file unnecessarily."
                    )
                    continue

                if not any(req in include_when for req in guards):
                    failures.append(
                        f"{including_path} (task #{idx+1}) includes tasks '{include_value}' "
                        f"-> {resolved}, but its 'when' does not contain the target's guard.\n"
                        f"Target guard(s): {guards}\n"
                        f"Include 'when': {include_when}\n"
                        "Add the guard condition to short-circuit when false."
                    )

        if failures:
            self.fail("Some include_tasks calls are missing pure-guard short-circuiting:\n\n" + "\n\n".join(failures))


if __name__ == "__main__":
    unittest.main()
