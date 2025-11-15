"""
Output Formatting Functions.

This module provides consistent formatting functions for timestamps, durations,
status codes, and tables across epycloud commands.

Functions
---------
format_timestamp : Format ISO 8601 timestamp with flexible format options
format_timestamp_full : Format timestamp as YYYY-MM-DD HH:MM:SS
format_timestamp_time : Format timestamp as HH:MM:SS only
format_duration : Format duration between two timestamps
format_status : Format workflow or batch job status with color coding
format_severity : Format log severity level with color coding
format_table : Format data as ASCII table with headers
parse_since_time : Parse relative time strings like "1h", "30m", "2d"
parse_duration_string : Parse duration strings to timedelta objects

Classes
-------
CapitalizedHelpFormatter : Custom argparse formatter with capitalized section titles
"""

import argparse
from datetime import UTC, datetime, timedelta


class CapitalizedHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """
    Custom help formatter that capitalizes section titles.

    Extends RawDescriptionHelpFormatter to:
    - Capitalize "usage:" to "Usage:"
    - Add newline after usage for better readability
    - Preserve raw formatting for description text
    """

    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = "Usage:\n  "
        return super().add_usage(usage, actions, groups, prefix)


def create_subparsers(parser: argparse.ArgumentParser, dest: str, **kwargs) -> argparse._SubParsersAction:
    """
    Create subparsers with consistent formatting applied automatically.

    This function wraps parser.add_subparsers() and applies the same
    monkey-patch used in cli.py to ensure all nested subcommands have:
    - CapitalizedHelpFormatter for "Usage:" capitalization
    - "Options" title (capitalized) instead of "options"

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parent parser to add subparsers to
    dest : str
        Destination attribute name for storing the subcommand
    **kwargs
        Additional arguments passed to add_subparsers()
        Common: title, help, description

    Returns
    -------
    argparse._SubParsersAction
        Subparsers object with monkey-patch applied

    Examples
    --------
    >>> parser = argparse.ArgumentParser()
    >>> subparsers = create_subparsers(parser, "subcommand", title="Subcommands")
    >>> sub = subparsers.add_parser("test", help="Test command")
    # The sub parser will automatically have CapitalizedHelpFormatter
    # and _optionals.title = "Options"
    """
    # Set default values for common kwargs
    defaults = {
        "help": "",
        "title": "Subcommands",
    }
    defaults.update(kwargs)

    # Create subparsers with defaults
    subparsers = parser.add_subparsers(dest=dest, **defaults)

    # Monkey-patch add_parser to automatically apply formatting
    original_add_parser = subparsers.add_parser

    def custom_add_parser(*args, **parse_kwargs):
        # Use CapitalizedHelpFormatter if no formatter_class specified
        if "formatter_class" not in parse_kwargs:
            parse_kwargs["formatter_class"] = CapitalizedHelpFormatter
        subparser = original_add_parser(*args, **parse_kwargs)
        # Capitalize Options title
        subparser._optionals.title = "Options"
        return subparser

    subparsers.add_parser = custom_add_parser

    return subparsers


def format_timestamp(iso_string: str, format: str = "full") -> str:
    """
    Format ISO 8601 timestamp with flexible format options.

    Parameters
    ----------
    iso_string : str
        ISO 8601 timestamp string (e.g., "2025-11-07T10:30:00Z").
    format : {"full", "time"}, optional
        Format type:
        - "full": YYYY-MM-DD HH:MM:SS
        - "time": HH:MM:SS only

    Returns
    -------
    str
        Formatted timestamp string. If parsing fails, returns truncated
        input string.

    Examples
    --------
    >>> format_timestamp("2025-11-07T10:30:00Z", "full")
    '2025-11-07 10:30:00'
    >>> format_timestamp("2025-11-07T10:30:00Z", "time")
    '10:30:00'
    """
    if format == "full":
        return format_timestamp_full(iso_string)
    elif format == "time":
        return format_timestamp_time(iso_string)
    else:
        return format_timestamp_full(iso_string)


def format_timestamp_full(iso_string: str) -> str:
    """
    Format ISO 8601 timestamp as YYYY-MM-DD HH:MM:SS.

    Parameters
    ----------
    iso_string : str
        ISO 8601 timestamp string (e.g., "2025-11-07T10:30:00Z").

    Returns
    -------
    str
        Formatted timestamp in YYYY-MM-DD HH:MM:SS format.
        If parsing fails, returns first 19 characters of input.

    Examples
    --------
    >>> format_timestamp_full("2025-11-07T10:30:00Z")
    '2025-11-07 10:30:00'
    >>> format_timestamp_full("2025-11-07T10:30:00.123456Z")
    '2025-11-07 10:30:00'
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError, TypeError):
        # Fallback: return first 19 chars (YYYY-MM-DDTHH:MM:SS)
        return iso_string[:19] if iso_string and len(iso_string) >= 19 else iso_string


def format_timestamp_time(iso_string: str) -> str:
    """
    Format ISO 8601 timestamp as HH:MM:SS only.

    Parameters
    ----------
    iso_string : str
        ISO 8601 timestamp string (e.g., "2025-11-07T10:30:00Z").

    Returns
    -------
    str
        Formatted time in HH:MM:SS format.
        If parsing fails, returns characters 11-19 of input (time portion).

    Examples
    --------
    >>> format_timestamp_time("2025-11-07T10:30:00Z")
    '10:30:00'
    >>> format_timestamp_time("2025-11-07T14:45:30.123456Z")
    '14:45:30'
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except (ValueError, AttributeError, TypeError):
        # Fallback: return chars 11-19 (HH:MM:SS portion)
        return iso_string[11:19] if iso_string and len(iso_string) >= 19 else iso_string


def format_duration(start: str, end: str = None) -> str:
    """
    Format duration between two timestamps as human-readable string.

    Parameters
    ----------
    start : str
        Start time as ISO 8601 timestamp.
    end : str, optional
        End time as ISO 8601 timestamp. If None, uses current time.

    Returns
    -------
    str
        Human-readable duration string (e.g., "2h 30m", "45s", "1d 3h").
        Returns "unknown" if parsing fails.

    Examples
    --------
    >>> format_duration("2025-11-07T10:00:00Z", "2025-11-07T12:30:00Z")
    '2h 30m'
    >>> format_duration("2025-11-07T10:00:00Z", "2025-11-07T10:00:45Z")
    '45s'
    >>> format_duration("2025-11-07T10:00:00Z", "2025-11-08T13:00:00Z")
    '1d 3h'
    """
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        if end:
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        else:
            end_dt = datetime.now(UTC)

        delta = end_dt - start_dt
        total_seconds = int(delta.total_seconds())

        if total_seconds < 0:
            return "0s"

        # Format based on magnitude
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            if seconds > 0:
                return f"{minutes}m {seconds}s"
            return f"{minutes}m"
        elif total_seconds < 86400:  # Less than 1 day
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}h {minutes}m"
            return f"{hours}h"
        else:  # 1 day or more
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            if hours > 0:
                return f"{days}d {hours}h"
            return f"{days}d"

    except (ValueError, AttributeError, TypeError):
        return "unknown"


def format_status(status: str, status_type: str = "workflow") -> str:
    """
    Format workflow or batch job status with ANSI color coding.

    Parameters
    ----------
    status : str
        Status string (e.g., "ACTIVE", "SUCCEEDED", "FAILED", "RUNNING").
    status_type : {"workflow", "batch"}, optional
        Type of status for appropriate color mapping, by default "workflow".

    Returns
    -------
    str
        Color-coded status string with ANSI escape codes.

    Notes
    -----
    Color mapping:
    - Green (32): SUCCEEDED, COMPLETED
    - Red (31): FAILED, CANCELLED
    - Yellow (33): ACTIVE, RUNNING, PENDING, QUEUED
    - Cyan (36): SCHEDULED
    - Default: No color

    Examples
    --------
    >>> format_status("SUCCEEDED")
    '\\033[32mSUCCEEDED\\033[0m'
    >>> format_status("FAILED")
    '\\033[31mFAILED\\033[0m'
    >>> format_status("RUNNING", "batch")
    '\\033[33mRUNNING\\033[0m'
    """
    from epycloud.lib.output import supports_color

    status_upper = status.upper() if status else ""

    # If colors disabled, return plain text
    if not supports_color():
        return status

    # Success states (green)
    if status_upper in ("SUCCEEDED", "COMPLETED", "SUCCESS"):
        return f"\033[32m{status}\033[0m"

    # Failure states (red)
    if status_upper in ("FAILED", "CANCELLED", "CANCELED", "FAILURE"):
        return f"\033[31m{status}\033[0m"

    # Active/running states (yellow)
    if status_upper in ("ACTIVE", "RUNNING", "PENDING", "QUEUED", "WORKING"):
        return f"\033[33m{status}\033[0m"

    # Scheduled (cyan)
    if status_upper in ("SCHEDULED",):
        return f"\033[36m{status}\033[0m"

    # Default: no color
    return status


def format_severity(severity: str) -> str:
    """
    Format log severity level with ANSI color coding.

    Parameters
    ----------
    severity : str
        Severity level (e.g., "ERROR", "WARNING", "INFO", "DEBUG").

    Returns
    -------
    str
        Color-coded severity string with ANSI escape codes.

    Notes
    -----
    Color mapping:
    - Red (31): ERROR, CRITICAL, EMERGENCY, ALERT
    - Yellow (33): WARNING, NOTICE
    - Blue (34): INFO
    - Cyan (36): DEBUG
    - Default: No color

    Examples
    --------
    >>> format_severity("ERROR")
    '\\033[31mERROR\\033[0m'
    >>> format_severity("WARNING")
    '\\033[33mWARNING\\033[0m'
    >>> format_severity("INFO")
    '\\033[34mINFO\\033[0m'
    """
    from epycloud.lib.output import supports_color

    severity_upper = severity.upper() if severity else ""

    # If colors disabled, return plain text
    if not supports_color():
        return severity

    # Error levels (red)
    if severity_upper in ("ERROR", "CRITICAL", "EMERGENCY", "ALERT"):
        return f"\033[31m{severity}\033[0m"

    # Warning levels (yellow)
    if severity_upper in ("WARNING", "NOTICE"):
        return f"\033[33m{severity}\033[0m"

    # Info level (blue)
    if severity_upper in ("INFO",):
        return f"\033[34m{severity}\033[0m"

    # Debug level (cyan)
    if severity_upper in ("DEBUG",):
        return f"\033[36m{severity}\033[0m"

    # Default: no color
    return severity


def format_table(headers: list[str], rows: list[list[str]], column_widths: list[int] = None) -> str:
    """
    Format data as ASCII table with headers and rows.

    Parameters
    ----------
    headers : list of str
        Column headers.
    rows : list of list of str
        Table rows, where each row is a list of cell values.
    column_widths : list of int, optional
        Fixed column widths. If None, auto-calculated from data.

    Returns
    -------
    str
        Formatted ASCII table with aligned columns and separator line.

    Examples
    --------
    >>> headers = ["Name", "Age", "City"]
    >>> rows = [["Alice", "30", "NYC"], ["Bob", "25", "SF"]]
    >>> print(format_table(headers, rows))
    Name   Age  City
    ----------------
    Alice  30   NYC
    Bob    25   SF

    >>> # Fixed widths
    >>> print(format_table(headers, rows, column_widths=[10, 5, 10]))
    Name        Age    City
    ---------------------------
    Alice       30     NYC
    Bob         25     SF
    """
    if not headers or not rows:
        return ""

    # Auto-calculate column widths if not provided
    if column_widths is None:
        column_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(column_widths):
                    column_widths[i] = max(column_widths[i], len(str(cell)))

    # Format header
    header_row = "  ".join(h.ljust(w) for h, w in zip(headers, column_widths))
    separator = "-" * len(header_row)

    # Format rows
    formatted_rows = []
    for row in rows:
        formatted_row = "  ".join(str(cell).ljust(w) for cell, w in zip(row, column_widths))
        formatted_rows.append(formatted_row)

    return "\n".join([header_row, separator] + formatted_rows)


def parse_since_time(since: str) -> datetime | None:
    """
    Parse relative time strings like "1h", "30m", "2d" into datetime objects.

    Parameters
    ----------
    since : str
        Relative time string with format: <number><unit>
        Supported units: h (hours), m (minutes), d (days), s (seconds)

    Returns
    -------
    datetime or None
        Datetime object representing the parsed time relative to now (UTC).
        Returns None if parsing fails.

    Examples
    --------
    >>> # Assuming current time is 2025-11-07 12:00:00 UTC
    >>> parse_since_time("1h")
    datetime.datetime(2025, 11, 7, 11, 0, 0, tzinfo=timezone.utc)
    >>> parse_since_time("30m")
    datetime.datetime(2025, 11, 7, 11, 30, 0, tzinfo=timezone.utc)
    >>> parse_since_time("2d")
    datetime.datetime(2025, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
    """
    if not since:
        return None

    try:
        # Parse format: <number><unit>
        if since.endswith("h"):
            hours = int(since[:-1])
            return datetime.now(UTC) - timedelta(hours=hours)
        elif since.endswith("m"):
            minutes = int(since[:-1])
            return datetime.now(UTC) - timedelta(minutes=minutes)
        elif since.endswith("d"):
            days = int(since[:-1])
            return datetime.now(UTC) - timedelta(days=days)
        elif since.endswith("s"):
            seconds = int(since[:-1])
            return datetime.now(UTC) - timedelta(seconds=seconds)
        else:
            # No unit specified, assume it's an ISO timestamp
            return datetime.fromisoformat(since.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def parse_duration_string(duration_str: str) -> timedelta | None:
    """
    Parse duration strings to timedelta objects.

    Parameters
    ----------
    duration_str : str
        Duration string with format: <number><unit>
        Supported units: h (hours), m (minutes), d (days), s (seconds)

    Returns
    -------
    timedelta or None
        Timedelta object representing the parsed duration.
        Returns None if parsing fails.

    Examples
    --------
    >>> parse_duration_string("2h")
    datetime.timedelta(hours=2)
    >>> parse_duration_string("30m")
    datetime.timedelta(minutes=30)
    >>> parse_duration_string("1d")
    datetime.timedelta(days=1)
    """
    if not duration_str:
        return None

    try:
        if duration_str.endswith("h"):
            hours = int(duration_str[:-1])
            return timedelta(hours=hours)
        elif duration_str.endswith("m"):
            minutes = int(duration_str[:-1])
            return timedelta(minutes=minutes)
        elif duration_str.endswith("d"):
            days = int(duration_str[:-1])
            return timedelta(days=days)
        elif duration_str.endswith("s"):
            seconds = int(duration_str[:-1])
            return timedelta(seconds=seconds)
        else:
            return None
    except (ValueError, TypeError):
        return None
