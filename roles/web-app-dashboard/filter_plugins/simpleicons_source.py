from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import requests
import re
import urllib3
from ansible.errors import AnsibleFilterError


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_requests_verify():
    """Reuse an explicit CA bundle when present, otherwise tolerate the local self-signed CA."""
    return os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or False


def slugify(name):
    """Convert a display name to a simple-icons slug format."""
    # Replace spaces and uppercase letters
    return re.sub(r"\s+", "", name.strip().lower())


def normalize_domain(value):
    """Extract a usable domain string from string/list/dict domain mappings."""
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
        return ""

    if isinstance(value, dict):
        for item in value.values():
            normalized = normalize_domain(item)
            if normalized:
                return normalized
        return ""

    return ""


def resolve_simpleicons_base(simpleicons_value, web_protocol="https"):
    """Resolve either a fully rendered base URL or a domain/domain mapping."""
    candidate = (
        simpleicons_value.get("web-svc-simpleicons")
        if isinstance(simpleicons_value, dict) and "web-svc-simpleicons" in simpleicons_value
        else simpleicons_value
    )
    normalized = normalize_domain(candidate)
    if not normalized:
        raise AnsibleFilterError("Simple Icons base URL or domain is required")

    if "{{" in normalized or "}}" in normalized or "{%" in normalized:
        raise AnsibleFilterError(
            "Simple Icons base URL/domain must be fully rendered before add_simpleicon_source runs"
        )

    if normalized.startswith(("http://", "https://")):
        return normalized.rstrip("/")

    return f"{web_protocol}://{normalized}"


def add_simpleicon_source(cards, simpleicons_value, web_protocol="https"):
    """
    For each card in portfolio_cards, check if an icon exists in the simpleicons server.
    If it does, add icon.source with the URL to the card entry.

    :param cards: List of card dictionaries (portfolio_cards)
    :param simpleicons_value: Fully rendered base URL, domain, or application domain mapping
    :param web_protocol: Protocol to use (https or http)
    :return: New list of cards with icon.source set when available
    """
    base_url = resolve_simpleicons_base(simpleicons_value, web_protocol)

    enhanced = []
    for card in cards:
        title = card.get("title", "")
        if not title:
            enhanced.append(card)
            continue
        # Create slug from title
        slug = slugify(title)
        icon_url = f"{base_url}/{slug}.svg"
        try:
            resp = requests.head(
                icon_url,
                timeout=2,
                allow_redirects=True,
                verify=get_requests_verify(),
            )
            if resp.status_code == 200:
                card.setdefault("icon", {})["source"] = icon_url
        except requests.RequestException:
            # Ignore network errors and move on
            pass
        enhanced.append(card)
    return enhanced


class FilterModule(object):
    """Ansible filter plugin to add simpleicons source URLs to portfolio cards"""

    def filters(self):
        return {
            "add_simpleicon_source": add_simpleicon_source,
        }
