from __future__ import absolute_import, division, print_function
__metaclass__ = type

import requests
import re
from ansible.errors import AnsibleFilterError


def slugify(name):
    """Convert a display name to a simple-icons slug format."""
    # Replace spaces and uppercase letters
    return re.sub(r'\s+', '', name.strip().lower())


def add_simpleicon_source(cards, domains, web_protocol='https'):
    """
    For each card in portfolio_cards, check if an icon exists in the simpleicons server.
    If it does, add icon.source with the URL to the card entry.

    :param cards: List of card dictionaries (portfolio_cards)
    :param domains: Mapping of application_id to domain names
    :param web_protocol: Protocol to use (https or http)
    :return: New list of cards with icon.source set when available
    """
    # Determine simpleicons service domain
    simpleicons_domain = domains.get('web-svc-simpleicons')
    if isinstance(simpleicons_domain, list):
        simpleicons_domain = simpleicons_domain[0]
    if not simpleicons_domain:
        raise AnsibleFilterError("Domain for 'simpleicons' not found in domains mapping")
    base_url = f"{web_protocol}://{simpleicons_domain}"

    enhanced = []
    for card in cards:
        title = card.get('title', '')
        if not title:
            enhanced.append(card)
            continue
        # Create slug from title
        slug = slugify(title)
        icon_url = f"{base_url}/{slug}.svg"
        try:
            resp = requests.head(icon_url, timeout=2)
            if resp.status_code == 200:
                card.setdefault('icon', {})['source'] = icon_url
        except requests.RequestException:
            # Ignore network errors and move on
            pass
        enhanced.append(card)
    return enhanced


class FilterModule(object):
    """Ansible filter plugin to add simpleicons source URLs to portfolio cards"""
    def filters(self):
        return {
            'add_simpleicon_source': add_simpleicon_source,
        }