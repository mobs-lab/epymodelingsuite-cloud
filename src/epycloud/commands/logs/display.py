"""Log display and formatting."""

import json
from typing import Any

from epycloud.lib.formatters import format_severity, format_timestamp_full, format_timestamp_time
from epycloud.lib.output import info


def display_logs(logs: list[dict[str, Any]]) -> None:
    """Display logs in readable format.

    Parameters
    ----------
    logs : list[dict[str, Any]]
        List of log entries
    """
    if not logs:
        info("No logs available")
        return

    print()

    # Display logs in chronological order (oldest first)
    for entry in reversed(logs):
        timestamp = entry.get("timestamp", "")
        severity = entry.get("severity", "INFO")
        text_payload = entry.get("textPayload", "")
        json_payload = entry.get("jsonPayload", {})

        # Get labels for context
        labels = entry.get("labels", {})
        stage = labels.get("stage", "")
        task_index = labels.get("batch.task_index", "")

        # Format timestamp
        if timestamp:
            time_str = format_timestamp_full(timestamp)
        else:
            time_str = "unknown"

        # Color code severity
        severity_display = format_severity(severity)

        # Build context string
        context_parts = []
        if stage:
            context_parts.append(f"stage={stage}")
        if task_index:
            context_parts.append(f"task={task_index}")

        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""

        # Get message text
        if text_payload:
            message = text_payload
        elif json_payload:
            message = json_payload.get("message", json.dumps(json_payload))
        else:
            message = ""

        # Sanitize message: replace newlines with spaces for single-line output
        message = message.replace("\n", " ").replace("\r", " ")

        # Display log entry on single line
        print(f"[{time_str}] {severity_display}{context_str} {message}")


def display_streaming_log_entry(entry: dict[str, Any]) -> str | None:
    """Format and display a single log entry for streaming mode.

    Parameters
    ----------
    entry : dict[str, Any]
        Log entry from Cloud Logging

    Returns
    -------
    str | None
        Timestamp of the entry (for tracking), or None if no timestamp
    """
    timestamp = entry.get("timestamp", "")
    severity = entry.get("severity", "INFO")
    text_payload = entry.get("textPayload", "")
    json_payload = entry.get("jsonPayload", {})

    # Format timestamp
    if timestamp:
        time_str = format_timestamp_time(timestamp)
    else:
        time_str = ""

    # Color code severity
    severity_display = format_severity(severity)

    # Display message (sanitize newlines for single-line output)
    if text_payload:
        sanitized = text_payload.replace("\n", " ").replace("\r", " ")
        print(f"[{time_str}] {severity_display}: {sanitized}")
    elif json_payload:
        message = json_payload.get("message", json.dumps(json_payload))
        sanitized = message.replace("\n", " ").replace("\r", " ")
        print(f"[{time_str}] {severity_display}: {sanitized}")

    return timestamp if timestamp else None
