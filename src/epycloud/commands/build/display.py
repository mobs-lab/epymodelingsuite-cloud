"""Display formatters for build command."""

from datetime import datetime

from epycloud.lib.formatters import (
    format_duration,
    format_status,
    format_timestamp_full,
)
from epycloud.lib.output import info


def display_build_status(builds: list[dict], limit: int) -> None:
    """Format and display build status in table format.

    Parameters
    ----------
    builds : list[dict]
        List of build dictionaries from gcloud
    limit : int
        Limit used for query (for display message)
    """
    from epycloud.lib.output import section_header

    if not builds:
        info("No builds found")
        return

    print()
    section_header("Recent Cloud Builds")

    # Header
    print("-" * 100)
    print(f"{'BUILD ID':<38} {'STATUS':<12} {'START TIME':<25} {'DURATION':<15}")
    print("-" * 100)

    # Rows
    for build in builds:
        build_id = build.get("id", "N/A")
        status = build.get("status", "UNKNOWN")
        start_time = build.get("startTime", "")
        finish_time = build.get("finishTime", "")

        # Format status with color
        status_formatted = format_status(status, "workflow")

        # Calculate padding needed for status (12 chars minus visible status length)
        # ANSI color codes are invisible, so we need to pad based on actual status text
        status_padding = 12 - len(status)
        status_with_padding = status_formatted + " " * status_padding

        # Format timestamp
        start_formatted = format_timestamp_full(start_time) if start_time else "N/A"

        # Calculate duration
        if start_time and finish_time:
            duration = format_duration(start_time, finish_time)
        elif start_time:
            # Ongoing build - show elapsed time
            duration = format_duration(start_time, datetime.now().isoformat())
        else:
            duration = "N/A"

        # Print with proper spacing
        print(f"{build_id:<38} {status_with_padding} {start_formatted:<25} {duration:<15}")

    print()
    info(f"Showing {len(builds)} build(s) (use --limit to adjust)")
    print()
