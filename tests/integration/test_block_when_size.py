# tests/integration/test_block_when_size.py
import unittest
from pathlib import Path
import yaml
from typing import Any, Dict, List, Tuple, Union

# -------- YAML loader that's tolerant of Ansible-specific tags (e.g. !vault) -----
class AnsibleTolerantLoader(yaml.SafeLoader):
    pass

def _ansible_tag_passthrough(loader: yaml.Loader, tag_prefix: str, node: yaml.Node):
    # Treat unknown/Ansible custom tags as plain YAML
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return None

yaml.add_multi_constructor('!', _ansible_tag_passthrough, Loader=AnsibleTolerantLoader)

# -------------------------------------------------------------------------------

def _repo_root() -> Path:
    """Find a plausible project root by walking upward from this file."""
    here = Path(__file__).resolve()
    cur = here.parent
    markers = {'.git', 'ansible.cfg', 'roles', 'playbook.yml'}
    for _ in range(7):
        if any((cur / m).exists() for m in markers):
            return cur
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    # Fallback: project/tests/integration/ -> pick parent of 'tests'
    return here.parents[2] if len(here.parents) >= 3 else here.parent

Yaml = Union[Dict[str, Any], List[Any], Any]

def _iter_yaml_files(root: Path) -> List[Path]:
    """Return all *.yml files in the repository (excluding common junk dirs)."""
    ignore_dirs = {'.git', '.venv', 'venv', '.tox', '.idea', '.pytest_cache', '__pycache__'}
    files: List[Path] = []
    for p in root.rglob('*.yml'):
        if any(part in ignore_dirs for part in p.parts):
            continue
        files.append(p)
    return files

def _safe_load_all(path: Path) -> List[Yaml]:
    """Load all YAML documents from a file, tolerating Ansible tags; return list of docs."""
    try:
        with path.open('r', encoding='utf-8') as fh:
            return list(yaml.load_all(fh, Loader=AnsibleTolerantLoader))
    except Exception:
        # If a file is completely unparsable, treat as empty (so test won't crash).
        return []

def _find_blocks_with_when(node: Yaml, path: str = "") -> List[Tuple[str, Dict[str, Any]]]:
    """
    Recursively find mappings that represent an Ansible block with a block-level `when`.
    Returns list of (yaml_path, block_mapping).
    """
    found: List[Tuple[str, Dict[str, Any]]] = []
    if isinstance(node, dict):
        if 'block' in node and 'when' in node and isinstance(node['block'], list):
            found.append((path or '/', node))
        # Recurse into all values to catch nested blocks
        for k, v in node.items():
            child_path = f"{path}/{k}" if path else f"/{k}"
            found.extend(_find_blocks_with_when(v, child_path))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            child_path = f"{path}[{i}]"
            found.extend(_find_blocks_with_when(item, child_path))
    return found

def _len_if_list(x: Any) -> int:
    return len(x) if isinstance(x, list) else 0

class BlockWhenSizeTest(unittest.TestCase):
    MAX_TASKS = 3  # performance threshold

    def test_blocks_with_when_and_sections_have_max_three_tasks(self):
        root = _repo_root()
        violations: List[str] = []

        for yml in _iter_yaml_files(root):
            docs = _safe_load_all(yml)
            if not docs:
                continue

            for doc_idx, doc in enumerate(docs):
                blocks = _find_blocks_with_when(doc, path=f"{yml}:{doc_idx}")
                for yaml_path, mapping in blocks:
                    name = mapping.get('name') or '<unnamed block>'
                    when_expr = mapping.get('when')

                    # Check main block size
                    block_tasks = mapping.get('block', [])
                    block_count = _len_if_list(block_tasks)
                    if block_count > self.MAX_TASKS:
                        violations.append(
                            f"[PERFORMANCE VIOLATION] {yml} :: {name} :: section=block "
                            f":: tasks={block_count} (> {self.MAX_TASKS}) "
                            f":: when={when_expr!r} :: at {yaml_path}"
                        )

                    # Check rescue size (if present)
                    rescue_tasks = mapping.get('rescue', [])
                    rescue_count = _len_if_list(rescue_tasks)
                    if rescue_count > self.MAX_TASKS:
                        violations.append(
                            f"[PERFORMANCE VIOLATION] {yml} :: {name} :: section=rescue "
                            f":: tasks={rescue_count} (> {self.MAX_TASKS}) "
                            f":: parent-when={when_expr!r} :: at {yaml_path}/rescue"
                        )

                    # Check always size (if present)
                    always_tasks = mapping.get('always', [])
                    always_count = _len_if_list(always_tasks)
                    if always_count > self.MAX_TASKS:
                        violations.append(
                            f"[PERFORMANCE VIOLATION] {yml} :: {name} :: section=always "
                            f":: tasks={always_count} (> {self.MAX_TASKS}) "
                            f":: parent-when={when_expr!r} :: at {yaml_path}/always"
                        )

        if violations:
            self.fail(
                "Blocks with a block-level 'when' must contain at most 3 tasks per section "
                "('block', 'rescue', 'always') for performance reasons.\n"
                "Rationale:\n"
                " - A block-level 'when' does NOT prevent parsing of tasks inside the block; "
                "   all sections ('block', 'rescue', 'always') are parsed and then may be skipped at runtime, "
                "   causing parse time and module redirect overhead.\n"
                "Recommendation:\n"
                " - Keep the block structure (for rescue/always, become, vars, etc.), but place a single "
                "   `include_tasks` INSIDE the respective section and put the condition on that include "
                "   (where feasible). When the condition is false, the included file is not parsed at all.\n"
                "Example:\n"
                " - Bad (heavy tasks directly in sections):\n"
                "     - block:\n"
                "         - community.general.pacman: name=foo state=present\n"
                "         - template: src=a.j2 dest=/a\n"
                "       rescue:\n"
                "         - debug: msg='rollback-1'\n"
                "         - debug: msg='rollback-2'\n"
                "       always:\n"
                "         - debug: msg='cleanup-1'\n"
                "       when: feature_enabled\n\n"
                " - Good (preserve semantics, avoid parsing when skipped):\n"
                "     - block:\n"
                "         - include_tasks: heavy_setup.yml\n"
                "           when: feature_enabled | bool\n"
                "       rescue:\n"
                "         - include_tasks: rollback.yml\n"
                "           when: feature_enabled | bool  # add a guard if rollback is heavy/rare\n"
                "       always:\n"
                "         - include_tasks: cleanup.yml\n"
                "           when: feature_enabled | bool  # add a guard if cleanup is heavy/rare\n"
                "       when: feature_enabled\n\n"
                "Violations:\n" + "\n".join(violations)
            )

if __name__ == "__main__":
    unittest.main()
