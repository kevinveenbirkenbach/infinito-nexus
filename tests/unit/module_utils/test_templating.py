# tests/unit/module_utils/test_templating.py
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from ansible.errors import AnsibleError


def _repo_root() -> Path:
    # __file__ = tests/unit/module_utils/test_templating.py
    return Path(__file__).resolve().parents[3]


# Ensure repo root is importable so `module_utils.*` resolves in all runners
import sys  # noqa: E402

sys.path.insert(0, str(_repo_root()))  # noqa: E402


from module_utils.templating import (  # noqa: E402
    render_ansible_strict,
)


class _FakeTemplarLookupUndefined:
    """
    Simulates the earlier failure:
      - templar exists
      - but cannot evaluate lookup()
      - returns string unchanged => must trigger fallback evaluator
    """

    def __init__(self):
        self.available_variables = {}

    def template(self, s, *args, **kwargs):
        # behave like templar that doesn't expand anything
        return s


class _FakeTemplarRejectsVariablesKwarg:
    """
    Simulates the earlier failure:
      Templar.template() got an unexpected keyword argument 'variables'
    We ensure our helper does NOT pass variables kwarg.
    """

    def __init__(self):
        self.available_variables = {}

    def template(self, s, fail_on_undefined=False):  # supports only these args
        # return something simple if variables were set via available_variables
        # We mimic minimal Jinja for a very specific case:
        if s.strip() == "{{ CA_ROOT.cert_host }}":
            ca_root = self.available_variables.get("CA_ROOT", {})
            return ca_root.get("cert_host", s)
        return s


class TestTemplatingRenderStrict(unittest.TestCase):
    def test_plain_string_passthrough(self):
        out = render_ansible_strict(
            templar=None,
            raw="/etc/infinito/ca/root-ca.crt",
            var_name="x",
            err_prefix="t",
            variables={},
        )
        self.assertEqual(out, "/etc/infinito/ca/root-ca.crt")

    def test_none_hard_fails(self):
        with self.assertRaises(AnsibleError):
            render_ansible_strict(
                templar=None,
                raw=None,
                var_name="x",
                err_prefix="t",
                variables={},
            )

    def test_empty_after_render_hard_fails(self):
        with self.assertRaises(AnsibleError):
            render_ansible_strict(
                templar=None,
                raw="  ",
                var_name="x",
                err_prefix="t",
                variables={},
            )

    def test_env_lookup_fallback_when_lookup_undefined_like(self):
        # Previously: 'lookup' is undefined -> string remained unchanged.
        # Now: fallback must resolve lookup('env', 'domain') (case-insensitive quoting)
        with patch.dict(os.environ, {"domain": "infinito.localhost"}, clear=False):
            out = render_ansible_strict(
                templar=_FakeTemplarLookupUndefined(),
                raw="{{ lookup('env', 'domain') | default('infinito.localhost', true) }}",
                var_name="CA_TRUST.trust_name",
                err_prefix="compose_ca_inject_cmd",
                variables={},
            )
        self.assertEqual(out, "infinito.localhost")

    def test_env_lookup_default_when_env_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            out = render_ansible_strict(
                templar=_FakeTemplarLookupUndefined(),
                raw="{{ lookup('env', 'DOMAIN') | default('infinito.localhost', true) }}",
                var_name="CA_TRUST.trust_name",
                err_prefix="compose_ca_inject_cmd",
                variables={},
            )
        self.assertEqual(out, "infinito.localhost")

    def test_ca_root_nested_var_resolves_without_templar(self):
        # This is the scenario that kept failing:
        # Rendered: /etc/{{ SOFTWARE_NAME | lower }}/ca/root-ca.crt
        # Raw: {{ CA_ROOT.cert_host }}
        #
        # We simulate CA_ROOT.cert_host itself being a Jinja string that requires another variable.
        variables = {
            "SOFTWARE_NAME": "Infinito.Nexus",
            "CA_ROOT": {
                "cert_host": "/etc/{{ SOFTWARE_NAME | lower }}/ca/root-ca.crt",
            },
        }
        out = render_ansible_strict(
            templar=None,  # no templar available -> must still resolve via fallback
            raw="{{ CA_ROOT.cert_host }}",
            var_name="CA_TRUST.cert_host",
            err_prefix="compose_ca_inject_cmd",
            variables=variables,
        )
        self.assertEqual(out, "/etc/infinito.nexus/ca/root-ca.crt")

    def test_templar_available_variables_is_used_no_variables_kwarg(self):
        # This covers the earlier crash:
        #   Templar.template() got an unexpected keyword argument 'variables'
        #
        # Our helper must not pass variables=..., but instead set available_variables.
        variables = {"CA_ROOT": {"cert_host": "/etc/infinito/ca/root-ca.crt"}}
        out = render_ansible_strict(
            templar=_FakeTemplarRejectsVariablesKwarg(),
            raw="{{ CA_ROOT.cert_host }}",
            var_name="CA_TRUST.cert_host",
            err_prefix="compose_ca_inject_cmd",
            variables=variables,
        )
        self.assertEqual(out, "/etc/infinito/ca/root-ca.crt")

    def test_unresolved_jinja_hard_fails(self):
        # If we cannot resolve, strict mode must hard fail (this matches your runtime failures).
        with self.assertRaises(AnsibleError):
            render_ansible_strict(
                templar=_FakeTemplarLookupUndefined(),
                raw="{{ DOES_NOT_EXIST }}",
                var_name="x",
                err_prefix="t",
                variables={},
            )

    def test_multi_round_rendering(self):
        # Ensure multi-pass rendering works:
        #   raw -> "{{ CA_ROOT.cert_host }}"
        #   CA_ROOT.cert_host -> "/etc/{{ SOFTWARE_NAME | lower }}/ca/root-ca.crt"
        variables = {
            "SOFTWARE_NAME": "Infinito.Nexus",
            "CA_ROOT": {"cert_host": "/etc/{{ SOFTWARE_NAME | lower }}/ca/root-ca.crt"},
        }
        out = render_ansible_strict(
            templar=_FakeTemplarLookupUndefined(),  # returns unchanged => fallback kicks in
            raw="{{ CA_ROOT.cert_host }}",
            var_name="x",
            err_prefix="t",
            variables=variables,
        )
        self.assertEqual(out, "/etc/infinito.nexus/ca/root-ca.crt")

    def test_embedded_expression_in_string(self):
        # Make sure embedded {{ ... }} inside a larger string is handled.
        variables = {"SOFTWARE_NAME": "Infinito.Nexus"}
        out = render_ansible_strict(
            templar=None,
            raw="/etc/{{ SOFTWARE_NAME | lower }}/ca/root-ca.crt",
            var_name="x",
            err_prefix="t",
            variables=variables,
        )
        self.assertEqual(out, "/etc/infinito.nexus/ca/root-ca.crt")

    def test_filters_lower_upper_default(self):
        variables = {"NAME": "MiXeD", "EMPTY": ""}
        out1 = render_ansible_strict(
            templar=None,
            raw="{{ NAME | lower }}",
            var_name="x",
            err_prefix="t",
            variables=variables,
        )
        self.assertEqual(out1, "mixed")

        out2 = render_ansible_strict(
            templar=None,
            raw="{{ NAME | upper }}",
            var_name="x",
            err_prefix="t",
            variables=variables,
        )
        self.assertEqual(out2, "MIXED")

        out3 = render_ansible_strict(
            templar=None,
            raw="{{ EMPTY | default('fallback', true) }}",
            var_name="x",
            err_prefix="t",
            variables=variables,
        )
        self.assertEqual(out3, "fallback")


if __name__ == "__main__":
    unittest.main()
