# filter_plugins/dotenv.py
#
# Dotenv-safe quoting for .env files.
#
# Rules:
# - Always use double quotes
# - Escape backslash and double quote
# - Do NOT do shell-style escaping
#
# Result is safe for:
# - docker compose --env-file
# - dotenv libraries (PHP, Ruby, Node, Python)
# - passwords containing ', $, spaces, !
#
from __future__ import annotations


class FilterModule:
    def filters(self):
        return {
            "dotenv_quote": self.dotenv_quote,
        }

    @staticmethod
    def dotenv_quote(value):
        """
        Quote a value for use in a .env file.

        Example:
          password -> "pa$'ss\"word"

        """
        if value is None:
            return '""'

        s = str(value)

        # Escape backslash first, then double quotes
        s = s.replace("\\", "\\\\")
        s = s.replace('"', '\\"')

        return f'"{s}"'
