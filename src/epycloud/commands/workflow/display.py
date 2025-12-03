"""Display formatters for workflow command."""

import json
from typing import Any

from epycloud.lib.formatters import (
    format_duration,
    format_severity,
    format_status,
    format_timestamp_full,
    format_timestamp_time,
)
from epycloud.lib.output import info


def display_execution_list(executions: list[dict[str, Any]], region: str) -> None:
    """Display list of executions.

    Parameters
    ----------
    executions : list[dict[str, Any]]
        List of execution objects
    region : str
        GCP region
    """
    from epycloud.lib.output import section_header

    print()
    section_header("Workflow executions")
    print("-" * 120)
    print(f"{'EXECUTION ID':<40} {'STATUS':<12} {'START TIME':<20} {'EXP_ID':<40}")
    print("-" * 120)

    for execution in executions:
        name = execution.get("name", "")
        execution_id = name.split("/")[-1] if name else "unknown"

        state = execution.get("state", "UNKNOWN")
        start_time = execution.get("startTime", "")

        # Try to extract exp_id from argument
        argument_str = execution.get("argument", "{}")
        exp_id = "unknown"
        try:
            arg = json.loads(argument_str)
            exp_id = arg.get("exp_id", "unknown")
        except json.JSONDecodeError:
            pass

        # Format start time
        start_time_str = format_timestamp_full(start_time) if start_time else "unknown"

        # Color code status (pad before coloring to avoid ANSI escape code width issues)
        status_padded = f"{state:<12}"
        status_display = format_status(status_padded, "workflow")

        print(f"{execution_id:<40} {status_display} {start_time_str:<20} {exp_id:<40}")

    print()
    info(f"Total: {len(executions)} execution(s)")
    print()


def display_execution_details(execution: dict[str, Any]) -> None:
    """Display detailed execution information.

    Parameters
    ----------
    execution : dict[str, Any]
        Execution object
    """
    from epycloud.lib.output import section_header

    name = execution.get("name", "")
    execution_id = name.split("/")[-1] if name else "unknown"

    print()
    section_header(f"Workflow execution: {execution_id}")
    print()

    # Basic info
    state = execution.get("state", "UNKNOWN")
    print(f"Status: {format_status(state, 'workflow')}")

    # Timestamps
    start_time = execution.get("startTime", "")
    if start_time:
        print(f"Start Time: {start_time}")

    end_time = execution.get("endTime", "")
    if end_time:
        print(f"End Time: {end_time}")

        # Calculate duration
        duration_str = format_duration(start_time, end_time)
        print(f"Duration: {duration_str}")

    # Workflow info
    workflow_revision_id = execution.get("workflowRevisionId", "")
    if workflow_revision_id:
        print(f"Workflow Revision: {workflow_revision_id}")

    # Arguments
    argument_str = execution.get("argument", "{}")
    print()
    print("Arguments:")
    try:
        arg = json.loads(argument_str)
        print(json.dumps(arg, indent=2))
    except json.JSONDecodeError:
        print(argument_str)

    # Result (if completed)
    result_str = execution.get("result", "")
    if result_str:
        print()
        print("Result:")
        try:
            result = json.loads(result_str)
            print(json.dumps(result, indent=2))
        except json.JSONDecodeError:
            print(result_str)

    # Error (if failed)
    error_obj = execution.get("error", {})
    if error_obj:
        print()
        print("\033[31mError:\033[0m")
        print(f"  Message: {error_obj.get('message', 'Unknown error')}")
        print(f"  Code: {error_obj.get('code', 'Unknown')}")

    # Status
    status = execution.get("status", {})
    if status:
        current_steps = status.get("currentSteps", [])
        if current_steps:
            print()
            print("Current Steps:")
            for step in current_steps:
                step_name = step.get("step", "unknown")
                print(f"  - {step_name}")

    print()


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
    for entry in reversed(logs):  # Most recent first
        timestamp = entry.get("timestamp", "")
        severity = entry.get("severity", "INFO")
        text_payload = entry.get("textPayload", "")
        json_payload = entry.get("jsonPayload", {})

        # Format timestamp
        time_str = format_timestamp_full(timestamp) if timestamp else "unknown"

        # Color code severity
        severity_display = format_severity(severity)

        # Display log entry
        print(f"[{time_str}] {severity_display}")

        if text_payload:
            print(f"  {text_payload}")
        elif json_payload:
            print(f"  {json.dumps(json_payload, indent=2)}")

        print()


def display_log_stream(entry: dict[str, Any]) -> str | None:
    """Display a single log entry in stream format.

    Parameters
    ----------
    entry : dict[str, Any]
        Log entry

    Returns
    -------
    str | None
        Timestamp of the log entry (for tracking), or None if no timestamp
    """
    timestamp = entry.get("timestamp", "")
    severity = entry.get("severity", "INFO")
    text_payload = entry.get("textPayload", "")

    # Format timestamp
    time_str = format_timestamp_time(timestamp) if timestamp else ""

    # Color code severity
    severity_display = format_severity(severity)

    # Sanitize message: replace newlines with spaces for single-line output
    sanitized = text_payload.replace("\n", " ").replace("\r", " ")
    print(f"[{time_str}] {severity_display}: {sanitized}")

    return timestamp if timestamp else None
