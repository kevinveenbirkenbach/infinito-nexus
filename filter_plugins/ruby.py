#
# Ansible filter for safely embedding values into Ruby double-quoted strings.
#
# Example:
#   {{ my_password | ruby_dq }}
#
# Output:
#   "escaped_value"
#
# Safe for GitLab Omnibus (gitlab.rb), Chef, Ruby DSLs.

class FilterModule:
    def filters(self):
        return {
            "ruby_dq": self.ruby_double_quoted_string,
        }

    @staticmethod
    def ruby_double_quoted_string(value):
        """
        Escape a value for use inside a Ruby double-quoted string
        and wrap it in double quotes.

        Ruby rules handled:
        - "  -> \"
        - \  -> \\
        - newlines -> \n
        - carriage return -> \r
        - tab -> \t

        NOT escaped on purpose:
        - $
        - €
        - !
        - '
        """

        if value is None:
            return '""'

        s = str(value)

        # Escape backslash first
        s = s.replace("\\", "\\\\")

        # Escape double quotes
        s = s.replace('"', '\\"')

        # Escape control characters
        s = s.replace("\n", "\\n")
        s = s.replace("\r", "\\r")
        s = s.replace("\t", "\\t")

        return f'"{s}"'
