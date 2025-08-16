import unittest
import os
import yaml
import re
from glob import glob


class TestVariableDefinitions(unittest.TestCase):
    """
    Ensures that every Jinja2 variable used in templates/playbooks is defined
    somewhere in the repository (direct var files, set_fact/vars blocks,
    loop_var/register names, Jinja set/for definitions, and Jinja macro parameters).

    If a variable is not defined, the test passes only if a corresponding
    fallback key exists (either "default_<var>" or "defaults_<var>").
    """

    def setUp(self):
        # Project root = repo root (tests/integration/.. -> ../../)
        self.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../')
        )

        # Collect all variable definition files: roles/*/{vars,defaults}/**/*.yml and group_vars/all/*.yml
        self.var_files = []
        patterns = [
            os.path.join(self.project_root, 'roles', '*', 'vars', '**', '*.yml'),
            os.path.join(self.project_root, 'roles', '*', 'defaults', '**', '*.yml'),
            os.path.join(self.project_root, 'group_vars', 'all', '*.yml'),
        ]
        for pat in patterns:
            self.var_files.extend(glob(pat, recursive=True))

        # File extensions to scan for Jinja usage/inline definitions
        self.scan_extensions = {'.yml', '.j2'}

        # -----------------------
        # Regex patterns
        # -----------------------

        # Simple {{ var }} usage with optional Jinja filters after a pipe
        self.simple_var_pattern = re.compile(r"{{\s*([a-zA-Z_]\w*)\s*(?:\|[^}]*)?}}")

        # {% set var = ... %}   (allow trimmed variants)
        self.jinja_set_def = re.compile(r'{%\s*-?\s*set\s+([a-zA-Z_]\w*)\s*=')

        # {% for x in ... %}  or  {% for k, v in ... %}   (allow trimmed variants)
        self.jinja_for_def = re.compile(
            r'{%\s*-?\s*for\s+([a-zA-Z_]\w*)(?:\s*,\s*([a-zA-Z_]\w*))?\s+in'
        )

        # {% macro name(param1, param2=..., *varargs, **kwargs) %}   (allow trimmed variants)
        self.jinja_macro_def = re.compile(
            r'{%\s*-?\s*macro\s+[a-zA-Z_]\w*\s*\((.*?)\)\s*-?%}'
        )

        # Ansible YAML anchors for inline var declarations
        # Support short and FQCN forms, plus inline dict after colon
        self.ansible_set_fact = re.compile(
            r'^(?:\s*-\s*)?(?:ansible\.builtin\.)?set_fact\s*:\s*(\{[^}]*\})?\s*$'
        )
        self.ansible_vars_block = re.compile(r'^(?:\s*[-]\s*)?vars\s*:\s*$')
        self.ansible_loop_var = re.compile(r'^\s*loop_var\s*:\s*([a-zA-Z_]\w*)')
        self.mapping_key = re.compile(r'^\s*([a-zA-Z_]\w*)\s*:\s*')
        self.register_pat = re.compile(r'^\s*register\s*:\s*([a-zA-Z_]\w*)')

        # -----------------------
        # Collect "defined" names
        # -----------------------
        self.defined = set()

        # 1) Keys from var files (top-level dict keys)
        for vf in self.var_files:
            try:
                with open(vf, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    self.defined.update(data.keys())
            except Exception:
                # Ignore unreadable/invalid YAML files
                pass

        # 2) Inline definitions across all scanned files
        for root, _, files in os.walk(self.project_root):
            for fn in files:
                ext = os.path.splitext(fn)[1]
                if ext not in self.scan_extensions:
                    continue

                path = os.path.join(root, fn)

                # Track when we're inside set_fact:/vars: blocks to also extract mapping keys.
                in_set_fact = False
                set_fact_indent = 0
                in_vars_block = False
                vars_block_indent = 0

                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            stripped = line.lstrip()
                            indent = len(line) - len(stripped)

                            # --- set_fact (short and FQCN), supports inline and block forms
                            m_sf = self.ansible_set_fact.match(stripped)
                            if m_sf:
                                inline_map = m_sf.group(1)
                                if inline_map:
                                    # Inline mapping: set_fact: { a: 1, b: 2 }
                                    try:
                                        data = yaml.safe_load(inline_map)
                                        if isinstance(data, dict):
                                            self.defined.update(
                                                k for k in data.keys() if isinstance(k, str)
                                            )
                                    except Exception:
                                        pass
                                    # do not enter block mode if inline present
                                    in_set_fact = False
                                else:
                                    # Block mapping: keys on subsequent indented lines
                                    in_set_fact = True
                                    set_fact_indent = indent
                                    # continue to next iteration to avoid double-processing this line
                                    continue

                            if in_set_fact:
                                # Still inside set_fact child mapping?
                                if indent > set_fact_indent and stripped.strip():
                                    m = self.mapping_key.match(stripped)
                                    if m:
                                        self.defined.add(m.group(1))
                                    # do not continue; still scan for Jinja defs below
                                else:
                                    # Leaving the block when indentation decreases or a new key at same level appears
                                    if indent <= set_fact_indent and stripped:
                                        in_set_fact = False

                            # --- vars: block (collect mapping keys)
                            if self.ansible_vars_block.match(stripped):
                                in_vars_block = True
                                vars_block_indent = indent
                                # continue to next line to avoid double-processing this line
                                continue

                            if in_vars_block:
                                # Inside vars: collect top-level mapping keys
                                if indent > vars_block_indent and stripped.strip():
                                    m = self.mapping_key.match(stripped)
                                    if m:
                                        self.defined.add(m.group(1))
                                    # do not continue; still scan for Jinja defs below
                                else:
                                    # Leaving vars block
                                    if indent <= vars_block_indent and stripped:
                                        in_vars_block = False

                            # --- Always scan every line (including inside blocks) for Jinja definitions

                            # {% set var = ... %}
                            for m in self.jinja_set_def.finditer(line):
                                self.defined.add(m.group(1))

                            # {% for x [, y] in ... %}
                            for m in self.jinja_for_def.finditer(line):
                                self.defined.add(m.group(1))
                                if m.group(2):
                                    self.defined.add(m.group(2))

                            # {% macro name(params...) %}
                            for m in self.jinja_macro_def.finditer(line):
                                params_blob = m.group(1)
                                params = [p.strip() for p in params_blob.split(',')]
                                for p in params:
                                    if not p:
                                        continue
                                    # Strip * / ** for varargs/kwargs
                                    p = p.lstrip('*')
                                    # Drop default value part: name=...
                                    name = p.split('=', 1)[0].strip()
                                    if re.match(r'^[a-zA-Z_]\w*$', name):
                                        self.defined.add(name)

                            # --- loop_var and register names
                            m_loop = self.ansible_loop_var.match(stripped)
                            if m_loop:
                                self.defined.add(m_loop.group(1))

                            m_reg = self.register_pat.match(stripped)
                            if m_reg:
                                self.defined.add(m_reg.group(1))

                except Exception:
                    # Ignore unreadable files
                    pass

    def test_all_used_vars_are_defined(self):
        """
        Scan all template/YAML files for {{ var }} usage and fail if a variable
        is not known as defined and has no fallback keys (default_<var>/defaults_<var>).
        """
        undefined_uses = []

        for root, _, files in os.walk(self.project_root):
            for fn in files:
                ext = os.path.splitext(fn)[1]
                if ext not in self.scan_extensions:
                    continue

                path = os.path.join(root, fn)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        for lineno, line in enumerate(f, 1):
                            for m in self.simple_var_pattern.finditer(line):
                                var = m.group(1)

                                # Skip well-known Jinja/Ansible builtins and frequent loop aliases
                                if var in (
                                    'lookup', 'role_name', 'domains', 'item', 'host_type',
                                    'inventory_hostname', 'role_path', 'playbook_dir',
                                    'ansible_become_password', 'inventory_dir', 'ansible_memtotal_mb'
                                ):
                                    continue

                                # Accept if defined directly or via fallback defaults
                                if (
                                    var not in self.defined
                                    and f"default_{var}" not in self.defined
                                    and f"defaults_{var}" not in self.defined
                                ):
                                    undefined_uses.append(
                                        f"{path}:{lineno}: '{{{{ {var} }}}}' used but not defined"
                                    )
                except Exception:
                    # Ignore unreadable files
                    pass

        if undefined_uses:
            self.fail(
                "Undefined Jinja2 variables found (no fallback 'default_' or 'defaults_' key):\n"
                + "\n".join(undefined_uses)
            )


if __name__ == '__main__':
    unittest.main()
