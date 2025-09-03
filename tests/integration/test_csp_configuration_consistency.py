import unittest
import yaml
from pathlib import Path
from urllib.parse import urlparse

class TestCspConfigurationConsistency(unittest.TestCase):
    SUPPORTED_DIRECTIVES = {
        'default-src',
        'connect-src',
        'frame-ancestors',
        'frame-src',
        'script-src',
        'script-src-elem',
        'style-src',
        'style-src-elem',
        'font-src',
        'worker-src',
        'manifest-src',
        'media-src'
    }
    SUPPORTED_FLAGS = {'unsafe-eval', 'unsafe-inline'}

    def is_valid_whitelist_entry(self, entry: str) -> bool:
        """
        Accept entries that are:
          - Jinja expressions (contain '{{' and '}}')
          - Data or Blob URIs (start with 'data:' or 'blob:')
          - HTTP/HTTPS/WS/WSS URLs
        """
        if '{{' in entry and '}}' in entry:
            return True
        if entry.startswith(('data:', 'blob:')):
            return True
        if entry == '*':
            return True
        parsed = urlparse(entry)
        return parsed.scheme in ('http', 'https','ws', 'wss') and bool(parsed.netloc)

    def test_csp_configuration_structure(self):
        """
        Iterate all roles; for each config/main.yml that defines 'csp',
        assert that:
          - csp is a dict
          - its whitelist/flags/hashes keys only use supported directives
          - flags for each directive are a dict of {flag_name: bool}, with flag_name in SUPPORTED_FLAGS
          - whitelist entries are valid as per is_valid_whitelist_entry
          - hashes entries are str or list of non-empty str
        """
        roles_dir = Path(__file__).resolve().parent.parent.parent / "roles"
        errors = []

        for role_path in sorted(roles_dir.iterdir()):
            if not role_path.is_dir():
                continue

            cfg_file = role_path / "config" / "main.yml"
            if not cfg_file.exists():
                continue

            try:
                cfg = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as e:
                errors.append(f"{role_path.name}: YAML parse error: {e}")
                continue

            csp = cfg.get('server',{}).get('csp')
            if csp is None:
                continue  # nothing to check

            if not isinstance(csp, dict):
                errors.append(f"{role_path.name}: 'csp' must be a dict")
                continue

            # Ensure sub-sections are dicts
            for section in ('whitelist', 'flags', 'hashes'):
                if section in csp and not isinstance(csp[section], dict):
                    errors.append(f"{role_path.name}: csp.{section} must be a dict")

            # Validate whitelist
            wl = csp.get('whitelist', {})
            for directive, val in wl.items():
                if directive not in self.SUPPORTED_DIRECTIVES:
                    errors.append(f"{role_path.name}: whitelist contains unsupported directive '{directive}'")
                # val may be str or list
                values = [val] if isinstance(val, str) else (val if isinstance(val, list) else None)
                if values is None:
                    errors.append(f"{role_path.name}: whitelist.{directive} must be a string or list of strings")
                else:
                    for entry in values:
                        if not isinstance(entry, str) or not entry.strip():
                            errors.append(f"{role_path.name}: whitelist.{directive} contains empty or non-string entry")
                        elif not self.is_valid_whitelist_entry(entry):
                            errors.append(f"{role_path.name}: whitelist.{directive} entry '{entry}' is not a valid entry")

            # Validate flags
            fl = csp.get('flags', {})
            for directive, flag_dict in fl.items():
                if directive not in self.SUPPORTED_DIRECTIVES:
                    errors.append(f"{role_path.name}: flags contains unsupported directive '{directive}'")
                if not isinstance(flag_dict, dict):
                    errors.append(f"{role_path.name}: flags.{directive} must be a dict of flag_name->bool")
                    continue
                for flag_name, flag_val in flag_dict.items():
                    if flag_name not in self.SUPPORTED_FLAGS:
                        errors.append(f"{role_path.name}: flags.{directive} has unsupported flag '{flag_name}'")
                    if not isinstance(flag_val, bool):
                        errors.append(f"{role_path.name}: flags.{directive}.{flag_name} must be a boolean")

            # Validate hashes
            hs = csp.get('hashes', {})
            for directive, snippet_val in hs.items():
                if directive not in self.SUPPORTED_DIRECTIVES:
                    errors.append(f"{role_path.name}: hashes contains unsupported directive '{directive}'")
                snippets = [snippet_val] if isinstance(snippet_val, str) else (snippet_val if isinstance(snippet_val, list) else None)
                if snippets is None:
                    errors.append(f"{role_path.name}: hashes.{directive} must be a string or list of strings")
                else:
                    for snippet in snippets:
                        if not isinstance(snippet, str) or not snippet.strip():
                            errors.append(f"{role_path.name}: hashes.{directive} contains empty or non-string snippet")

        if errors:
            self.fail("CSP configuration validation failures:\n" + "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
