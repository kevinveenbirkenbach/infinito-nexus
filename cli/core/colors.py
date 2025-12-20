from __future__ import annotations

# Color support
try:
    from colorama import init as colorama_init, Fore, Style

    colorama_init(autoreset=True)
except ImportError:
    # Minimal ANSI fallback if colorama is not available
    class Style:  # type: ignore
        RESET_ALL = "\033[0m"
        BRIGHT = "\033[1m"
        DIM = "\033[2m"

    class Fore:  # type: ignore
        BLACK = "\033[30m"
        RED = "\033[31m"
        GREEN = "\033[32m"
        YELLOW = "\033[33m"
        BLUE = "\033[34m"
        MAGENTA = "\033[35m"
        CYAN = "\033[36m"
        WHITE = "\033[37m"


def color_text(text: str, color: str) -> str:
    return f"{color}{text}{Style.RESET_ALL}"
