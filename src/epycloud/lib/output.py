"""Pretty output and formatting utilities for epycloud CLI."""

import sys
from typing import Optional


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


def supports_color() -> bool:
    """Check if the terminal supports color output.

    Returns:
        True if colors are supported
    """
    # Check if stdout is a TTY and NO_COLOR is not set
    return sys.stdout.isatty() and not sys.platform.startswith("win")


def colorize(text: str, color: str) -> str:
    """Colorize text if terminal supports it.

    Args:
        text: Text to colorize
        color: ANSI color code

    Returns:
        Colorized text or plain text
    """
    if supports_color():
        return f"{color}{text}{Colors.RESET}"
    return text


def success(message: str) -> None:
    """Print success message with checkmark.

    Args:
        message: Success message
    """
    symbol = colorize("✓", Colors.GREEN)
    print(f"{symbol} {message}")


def error(message: str) -> None:
    """Print error message with X symbol.

    Args:
        message: Error message
    """
    symbol = colorize("✗", Colors.RED)
    print(f"{symbol} {message}", file=sys.stderr)


def warning(message: str) -> None:
    """Print warning message with warning symbol.

    Args:
        message: Warning message
    """
    symbol = colorize("⚠", Colors.YELLOW)
    print(f"{symbol} {message}")


def info(message: str) -> None:
    """Print info message.

    Args:
        message: Info message
    """
    print(f"  {message}")


def header(message: str) -> None:
    """Print header message.

    Args:
        message: Header message
    """
    text = colorize(message, Colors.BOLD)
    print(f"\n{text}")


def subheader(message: str) -> None:
    """Print subheader message.

    Args:
        message: Subheader message
    """
    text = colorize(message, Colors.CYAN)
    print(f"\n{text}")


def dim(message: str) -> None:
    """Print dimmed message.

    Args:
        message: Dimmed message
    """
    text = colorize(message, Colors.DIM)
    print(f"  {text}")


def ask_confirmation(message: str, default: bool = False) -> bool:
    """Ask user for confirmation.

    Args:
        message: Confirmation message
        default: Default value if user just presses Enter

    Returns:
        True if user confirmed, False otherwise
    """
    if default:
        prompt = f"{message} [Y/n]: "
    else:
        prompt = f"{message} [y/N]: "

    try:
        response = input(prompt).strip().lower()
        if not response:
            return default
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def print_key_value(key: str, value: str, indent: int = 0) -> None:
    """Print key-value pair with formatting.

    Args:
        key: Key to print
        value: Value to print
        indent: Indentation level
    """
    indent_str = "  " * indent
    key_colored = colorize(key, Colors.CYAN)
    print(f"{indent_str}{key_colored}: {value}")


def print_dict(data: dict, indent: int = 0) -> None:
    """Print dictionary with nice formatting.

    Args:
        data: Dictionary to print
        indent: Indentation level
    """
    for key, value in data.items():
        if isinstance(value, dict):
            key_colored = colorize(key, Colors.CYAN)
            print(f"{'  ' * indent}{key_colored}:")
            print_dict(value, indent + 1)
        else:
            print_key_value(key, str(value), indent)
