import os
import sys
import unittest

# Make the filter plugin importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
FILTER_PATH = os.path.join(ROOT, "roles", "sys-dns-parent-hosts", "filter_plugins")
if FILTER_PATH not in sys.path:
    sys.path.insert(0, FILTER_PATH)

from parent_dns import parent_build_records  # noqa: E402


def has_record(records, rtype, name, zone):
    """True if an exact (type, name, zone) record exists."""
    return any(
        r.get("type") == rtype and r.get("name") == name and r.get("zone") == zone
        for r in records
    )


def has_name_or_wildcard(records, rtype, label, zone):
    """True if either <label> or *.<label> exists for (type, zone)."""
    return has_record(records, rtype, label, zone) or has_record(
        records, rtype, f"*.{label}", zone
    )


class TestParentDNS(unittest.TestCase):
    def test_end_to_end_with_ipv6(self):
        current = {
            "web-app-foo": [
                "example.com",
                "wiki.example.com",
                "c.wiki.example.com",
                "a.b.example.com",
            ],
            "web-app-bar": ["foo.other.com"],  # different apex -> ignored
        }

        recs = parent_build_records(
            current_play_domains=current,
            apex="example.com",
            ip4="192.0.2.10",
            ip6="2001:db8::10",  # AAAA may or may not be emitted by role; treat as optional
            proxied=True,
            explicit_domains=None,
            include_apex=True,
            min_child_depth=2,
        )

        # Apex must resolve
        self.assertTrue(has_record(recs, "A", "@", "example.com"))

        # Parents may be plain or wildcard (or both)
        self.assertTrue(has_name_or_wildcard(recs, "A", "wiki", "example.com"))
        self.assertTrue(has_name_or_wildcard(recs, "A", "b", "example.com"))

        # AAAA optional: if present, at least apex AAAA must exist
        if any(r.get("type") == "AAAA" for r in recs):
            self.assertTrue(has_record(recs, "AAAA", "@", "example.com"))

        # Proxied flag is propagated
        self.assertTrue(all(r.get("proxied") is True for r in recs if r["type"] in ("A", "AAAA")))

    def test_explicit_domains_without_ipv6(self):
        explicit = ["example.com", "c.wiki.example.com", "x.y.example.com"]

        recs = parent_build_records(
            current_play_domains={"ignore": ["foo.example.com"]},
            apex="example.com",
            ip4="198.51.100.5",
            ip6="",  # No IPv6 -> no AAAA expected
            proxied=False,
            explicit_domains=explicit,
            include_apex=True,
            min_child_depth=2,
        )

        # Apex must resolve
        self.assertTrue(has_record(recs, "A", "@", "example.com"))

        # Parents may be plain or wildcard
        self.assertTrue(has_name_or_wildcard(recs, "A", "wiki", "example.com"))
        self.assertTrue(has_name_or_wildcard(recs, "A", "y", "example.com"))

        # No IPv6 supplied -> there should be no AAAA records
        self.assertFalse(any(r.get("type") == "AAAA" for r in recs))

    def test_current_play_domains_may_contain_dicts(self):
        # Dict values with strings and lists inside must be accepted and flattened.
        current = {
            "web-app-foo": {
                "prod": "wiki.example.com",
                "preview": ["c.wiki.example.com"],
            },
            "web-app-bar": ["irrelevant.other.com"],  # different apex, ignored
        }

        recs = parent_build_records(
            current_play_domains=current,
            apex="example.com",
            ip4="203.0.113.7",
            ip6=None,
            proxied=False,
            explicit_domains=None,
            include_apex=True,
            min_child_depth=2,
        )

        self.assertTrue(has_record(recs, "A", "@", "example.com"))
        self.assertTrue(has_name_or_wildcard(recs, "A", "wiki", "example.com"))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(Exception):
            parent_build_records(
                current_play_domains={"ok": ["example.com"]},
                apex="",  # invalid apex
                ip4="192.0.2.1",
            )

        with self.assertRaises(Exception):
            parent_build_records(
                current_play_domains={"ok": ["example.com"]},
                apex="example.com",
                ip4="",  # required
            )


if __name__ == "__main__":
    unittest.main()
