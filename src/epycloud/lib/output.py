"""Pretty output and formatting utilities for epycloud CLI."""

import os
import sys

# Global color state
_color_enabled = None  # None = auto-detect, "auto", "always", or "never"

# Global quiet state
_quiet_mode = False


def set_quiet_mode(enabled: bool) -> None:
    """Set quiet mode to suppress status messages.

    Parameters
    ----------
    enabled : bool
        True to suppress status messages, False to show them.
    """
    global _quiet_mode
    _quiet_mode = enabled


def set_color_enabled(mode: str) -> None:
    """
    Set color mode: 'auto', 'always', or 'never'.

    Parameters
    ----------
    mode : str
        Color mode: "auto" (detect TTY), "always" (force colors), or "never" (disable colors).

    Raises
    ------
    ValueError
        If mode is not one of "auto", "always", or "never".
    """
    global _color_enabled
    if mode not in ("auto", "always", "never"):
        raise ValueError(f"Invalid color mode: {mode}")
    _color_enabled = mode


# ANSI color codes
class Colors:
    """
    ANSI color codes for terminal output.

    Provides constants for text formatting and colorization in terminals
    that support ANSI escape sequences.
    """

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
    """
    Check if the terminal supports color output.

    Respects the color mode set via set_color_enabled() and the NO_COLOR
    environment variable (https://no-color.org/).

    Returns
    -------
    bool
        True if colors should be displayed, False otherwise.
    """
    global _color_enabled

    # If explicitly set to always, force colors
    if _color_enabled == "always":
        return True

    # If explicitly set to never, disable colors
    if _color_enabled == "never":
        return False

    # Auto mode (default): check NO_COLOR env var first
    if os.environ.get("NO_COLOR"):
        return False

    # Check if stdout is a TTY and not Windows
    return sys.stdout.isatty() and not sys.platform.startswith("win")


def colorize(text: str, color: str) -> str:
    """
    Colorize text if terminal supports it.

    Parameters
    ----------
    text : str
        Text to colorize.
    color : str
        ANSI color code from the Colors class.

    Returns
    -------
    str
        Colorized text if supported, plain text otherwise.
    """
    if supports_color():
        return f"{color}{text}{Colors.RESET}"
    return text


def success(message: str) -> None:
    """
    Print success message with green checkmark.

    Parameters
    ----------
    message : str
        Success message to display.
    """
    symbol = colorize("✓", Colors.GREEN)
    print(f"{symbol} {message}")


def error(message: str) -> None:
    """
    Print error message with red X symbol to stderr.

    Parameters
    ----------
    message : str
        Error message to display.
    """
    symbol = colorize("✗", Colors.RED)
    print(f"{symbol} {message}", file=sys.stderr)


def status(message: str) -> None:
    """Print status/progress message to stderr. Suppressed by --quiet.

    Parameters
    ----------
    message : str
        Status message to display.
    """
    if not _quiet_mode:
        print(f"  {message}", file=sys.stderr)


def warning(message: str) -> None:
    """
    Print warning message with yellow warning symbol.

    Parameters
    ----------
    message : str
        Warning message to display.
    """
    symbol = colorize("⚠", Colors.YELLOW)
    print(f"{symbol} {message}")


def info(message: str) -> None:
    """
    Print informational message with indentation.

    Parameters
    ----------
    message : str
        Informational message to display.
    """
    print(f"  {message}")


def header(message: str) -> None:
    """
    Print header message in bold.

    Parameters
    ----------
    message : str
        Header message to display.
    """
    text = colorize(message, Colors.BOLD)
    print(f"\n{text}")


def subheader(message: str) -> None:
    """
    Print subheader message in cyan.

    Parameters
    ----------
    message : str
        Subheader message to display.
    """
    text = colorize(message, Colors.CYAN)
    print(f"\n{text}")


def section_header(title: str) -> None:
    """
    Print section header in cyan with bracket style.

    This follows the consistent style used across status, workflow, and build commands.
    The header is displayed as [Title] in cyan color (if supported).

    Parameters
    ----------
    title : str
        Section title to display.

    Examples
    --------
    >>> section_header("Recent Cloud Builds")
    [Recent Cloud Builds]  # In cyan if color is supported
    """
    if supports_color():
        print(f"\033[36m[{title}]\033[0m")
    else:
        print(f"[{title}]")


def dim(message: str) -> None:
    """
    Print dimmed message with indentation.

    Parameters
    ----------
    message : str
        Dimmed message to display.
    """
    text = colorize(message, Colors.DIM)
    print(f"  {text}")


def ask_confirmation(message: str, default: bool = False) -> bool:
    """
    Ask user for yes/no confirmation.

    Parameters
    ----------
    message : str
        Confirmation question to ask.
    default : bool, optional
        Default value if user just presses Enter, by default False.

    Returns
    -------
    bool
        True if user confirmed (y/yes), False otherwise.

    Examples
    --------
    >>> if ask_confirmation("Delete all files?"):
    ...     print("Deleting files...")
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
    """
    Print key-value pair with formatting and indentation.

    Parameters
    ----------
    key : str
        Key to print (displayed in cyan).
    value : str
        Value to print.
    indent : int, optional
        Indentation level (number of 2-space indents), by default 0.
    """
    indent_str = "  " * indent
    key_colored = colorize(key, Colors.CYAN)
    print(f"{indent_str}{key_colored}: {value}")


def print_dict(data: dict, indent: int = 0) -> None:
    """
    Print dictionary with hierarchical formatting.

    Recursively prints nested dictionaries with proper indentation
    and color coding. At the top level (indent=0), adds blank lines
    between sections for better readability.

    Parameters
    ----------
    data : dict
        Dictionary to print.
    indent : int, optional
        Indentation level (number of 2-space indents), by default 0.
    """
    items = list(data.items())
    for i, (key, value) in enumerate(items):
        if isinstance(value, dict):
            key_colored = colorize(key, Colors.CYAN)
            print(f"{'  ' * indent}{key_colored}:")
            print_dict(value, indent + 1)
            # Add blank line after top-level sections (except the last one)
            if indent == 0 and i < len(items) - 1:
                print()
        else:
            print_key_value(key, str(value), indent)
