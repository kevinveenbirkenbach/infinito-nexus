# Compatibility shim – use utils.annotations.message instead.
from utils.annotations.message import (  # noqa: F401
    _emit,
    error,
    error_each,
    in_github_actions,
    notice,
    warning,
    warning_each,
)
