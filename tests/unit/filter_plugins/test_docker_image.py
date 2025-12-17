#!/usr/bin/env python3

import os
import sys
import unittest
from filter_plugins.get_docker_image import FilterModule

class TestGetDockerImage(unittest.TestCase):
    def setUp(self):
        self.get_docker_image = FilterModule().filters()["get_docker_image"]

    def test_version_from_docker_versions(self):
        applications = {
            "akaunting": {
                "version": "1.0.0",
                "docker": {
                    "images": {"akaunting": "docker.io/akaunting/akaunting"},
                    "versions": {"akaunting": "2.0.0"}
                }
            }
        }
        result = self.get_docker_image(applications, "akaunting", "akaunting")
        self.assertEqual(result, "docker.io/akaunting/akaunting:2.0.0")

    def test_missing_image_raises_error(self):
        applications = {
            "akaunting": {
                "version": "1.0.0",
                "docker": {
                    "images": {},
                    "versions": {}
                }
            }
        }
        with self.assertRaises(ValueError):
            self.get_docker_image(applications, "akaunting", "akaunting")

    def test_missing_version_raises_error(self):
        applications = {
            "akaunting": {
                "docker": {
                    "images": {"akaunting": "some/image"},
                    "versions": {}
                }
            }
        }
        with self.assertRaises(ValueError):
            self.get_docker_image(applications, "akaunting", "akaunting")

    # --- new: Default image_key uses application_id if none provided ---
    def test_default_image_key_uses_application_id(self):
        applications = {
            "myapp": {
                "version": "3.0.0",
                "docker": {
                    "images": {"myapp": "registry/myapp"},
                    "versions": {"myapp": "4.5.6"}
                }
            }
        }
        # No image_key argument → falls back to application_id
        result = self.get_docker_image(applications, "myapp")
        self.assertEqual(result, "registry/myapp:4.5.6")

    # --- new: Alternate image_key lookup ---
    def test_alternate_image_key(self):
        applications = {
            "service": {
                "version": "9.9.9",
                "docker": {
                    "images": {
                        "service": "registry/service",
                        "db":      "registry/service-db"
                    },
                    "versions": {
                        "db": "2.2.2"
                    }
                }
            }
        }
        result = self.get_docker_image(applications, "service", "db")
        self.assertEqual(result, "registry/service-db:2.2.2")

    # --- new: Missing application raises error ---
    def test_missing_application_raises_error(self):
        applications = {}
        with self.assertRaises(ValueError):
            self.get_docker_image(applications, "does_not_exist")

if __name__ == "__main__":
    unittest.main()
