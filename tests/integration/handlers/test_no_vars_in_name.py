import unittest
import yaml
from pathlib import Path


class HandlerNameIntegrationTest(unittest.TestCase):
    """
    Integration test to ensure that handler definitions in Ansible roles
    do not include Jinja variable interpolations in their 'name' attribute.
    """

    def test_handlers_have_no_variables_in_name(self):
        # Locate all handler YAML files under roles/*/handlers/
        handler_files = Path("roles").glob("*/handlers/*.yml")
        for handler_file in handler_files:
            with self.subTest(handler_file=str(handler_file)):
                content = handler_file.read_text(encoding="utf-8")
                # Load all documents in the YAML file
                documents = list(yaml.safe_load_all(content))
                for index, doc in enumerate(documents):
                    if not isinstance(doc, dict):
                        continue
                    # Only consider entries that are handlers (they have a 'listen' key)
                    if "listen" in doc:
                        name = doc.get("name", "")
                        # Assert that no Jinja interpolation is present in the name
                        self.assertNotRegex(
                            name,
                            r"{{.*}}",
                            msg=(
                                f"Handler 'name' in file {handler_file} document #{index} "
                                f"contains a Jinja variable: {name}"
                            ),
                        )


if __name__ == "__main__":
    unittest.main()
