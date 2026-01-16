from __future__ import absolute_import, division, print_function

__metaclass__ = type

import glob
import os
import re
import yaml

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError
from module_utils.config_utils import get_app_conf


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        """
        This lookup iterates over all roles whose folder name starts with 'web-app-'
        and generates a list of dictionaries (cards). For each role, it:

          - Reads application_id from the role's vars/main.yml
          - Reads the title from the role's README.md (the first H1 line)
          - Retrieves the description from galaxy_info.description in meta/main.yml
          - Retrieves the icon class from galaxy_info.logo.class
          - Retrieves the tags from galaxy_info.galaxy_tags
          - Builds the URL using the 'domains' variable
          - Sets the iframe flag from applications | get_app_conf(application_id, 'docker.services.desktop.enabled', True)

        Only cards whose application_id is included in the variable group_names are returned.
        """
        # Default to "roles" directory if no path is provided
        roles_dir = terms[0] if len(terms) > 0 else "roles"
        cards = []

        # Retrieve group_names from variables (used to filter roles)
        group_names = variables.get("group_names", [])

        # Search for all roles starting with "web-app-"
        pattern = os.path.join(roles_dir, "web-app-*")
        for role_path in glob.glob(pattern):
            role_dir = role_path.rstrip("/")
            role_basename = os.path.basename(role_dir)

            # Skip roles not starting with "web-app-"
            if not role_basename.startswith("web-app-"):  # Ensure prefix
                continue

            # Load application_id from role's vars/main.yml
            vars_path = os.path.join(role_dir, "vars", "main.yml")
            try:
                if not os.path.isfile(vars_path):
                    raise AnsibleError(
                        f"Vars file not found for role '{role_basename}': {vars_path}"
                    )
                with open(vars_path, "r", encoding="utf-8") as vf:
                    vars_content = vf.read()
                vars_data = yaml.safe_load(vars_content) or {}
                application_id = vars_data.get("application_id")
                if not application_id:
                    raise AnsibleError(f"Key 'application_id' not found in {vars_path}")
            except Exception as e:
                raise AnsibleError(
                    f"Error getting application_id for role '{role_basename}': {e}"
                )

            # Skip roles not listed in group_names
            if application_id not in group_names:
                continue

            # Define paths to README.md and meta/main.yml
            readme_path = os.path.join(role_dir, "README.md")
            meta_path = os.path.join(role_dir, "meta", "main.yml")

            # Skip role if required files are missing
            if not os.path.exists(readme_path) or not os.path.exists(meta_path):
                continue

            # Extract title from first H1 line in README.md
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    readme_content = f.read()
                title_match = re.search(r"^#\s+(.*)$", readme_content, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else application_id
            except Exception as e:
                raise AnsibleError(f"Error reading '{readme_path}': {e}")

            # Extract metadata from meta/main.yml
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_data = yaml.safe_load(f) or {}

                galaxy_info = meta_data.get("galaxy_info", {})
                # If display is set to False ignore it
                if not galaxy_info.get("display", True):
                    continue

                description = galaxy_info.get("description", "")
                logo = galaxy_info.get("logo", {})
                icon_class = logo.get("class", "fa-solid fa-cube")
                tags = galaxy_info.get("galaxy_tags", [])
            except Exception as e:
                raise AnsibleError(f"Error reading '{meta_path}': {e}")

            # Retrieve domains and applications from the variables
            domains = variables.get("domains", {})
            applications = variables.get("applications", {})
            domain_url = domains.get(application_id, "")

            if isinstance(domain_url, list):
                domain_url = domain_url[0]
            elif isinstance(domain_url, dict):
                domain_url = next(iter(domain_url.values()))

            if "WEB_PROTOCOL" not in variables:
                raise AnsibleError("WEB_PROTOCOL is required to build application URLs")

            protocol = self._templar.template(variables["WEB_PROTOCOL"]).strip()

            # domain_url kann list/dict sein; nach deiner Normalisierung:
            domain_url = self._templar.template(domain_url).strip() if domain_url else ""

            url = f"{protocol}://{domain_url}" if domain_url else ""

            iframe = get_app_conf(
                applications,
                application_id,
                "docker.services.desktop.enabled",
                strict=False,
                default=False,
            )

            # Build card dictionary
            card = {
                "icon": {"class": icon_class},
                "title": title,
                "text": description,
                "url": url,
                "link_text": f"Explore {title}",
                "iframe": iframe,
                "tags": tags,
            }

            cards.append(card)

        # Sort A-Z
        cards.sort(key=lambda c: c["title"].lower())

        # Return the list of cards
        return [cards]
