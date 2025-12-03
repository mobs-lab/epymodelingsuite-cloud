"""Workflow command for managing Cloud Workflows executions.

Available subcommands:
    epycloud workflow list       List workflow executions
    epycloud workflow describe   Describe execution details
    epycloud workflow logs       Stream execution logs
    epycloud workflow cancel     Cancel a running execution
    epycloud workflow retry      Retry a failed execution
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from typing import Any

import requests

from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import (
    get_gcloud_access_token,
    require_config,
)
from epycloud.lib.formatters import (
    create_subparsers,
    format_duration,
    format_severity,
    format_status,
    format_timestamp_full,
    format_timestamp_time,
    parse_since_time,
)
from epycloud.lib.output import error, info, success, warning


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the workflow command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "workflow",
        help="Manage Cloud Workflows executions",
        description="List, describe, monitor, and manage workflow executions",
    )

    # Store parser for help printing
    parser.set_defaults(_workflow_parser=parser)

    # Create subcommands with consistent formatting
    workflow_subparsers = create_subparsers(parser, "workflow_subcommand")

    # ========== workflow list ==========
    list_parser = workflow_subparsers.add_parser(
        "list",
        help="List workflow executions",
    )

    list_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of executions to show (default: 20)",
    )

    list_parser.add_argument(
        "--status",
        choices=["ACTIVE", "SUCCEEDED", "FAILED", "CANCELLED"],
        help="Filter by status",
    )

    list_parser.add_argument(
        "--exp-id",
        help="Filter by experiment ID",
    )

    list_parser.add_argument(
        "--since",
        help="Show executions since (e.g., 24h, 7d, 30m)",
    )

    # ========== workflow describe ==========
    describe_parser = workflow_subparsers.add_parser(
        "describe",
        help="Describe execution details",
    )

    describe_parser.add_argument(
        "execution_id",
        help="Execution ID or full execution name",
    )

    # ========== workflow logs ==========
    logs_parser = workflow_subparsers.add_parser(
        "logs",
        help="Stream execution logs",
    )

    logs_parser.add_argument(
        "execution_id",
        help="Execution ID or full execution name",
    )

    logs_parser.add_argument(
        "--follow",
        "-f",
        action="store_true",
        help="Follow log output (stream mode)",
    )

    logs_parser.add_argument(
        "--tail",
        type=int,
        default=100,
        help="Show last N lines (default: 100)",
    )

    # ========== workflow cancel ==========
    cancel_parser = workflow_subparsers.add_parser(
        "cancel",
        help="Cancel running execution",
    )

    cancel_parser.add_argument(
        "execution_id",
        help="Execution ID or full execution name",
    )

    # ========== workflow retry ==========
    retry_parser = workflow_subparsers.add_parser(
        "retry",
        help="Retry failed execution",
    )

    retry_parser.add_argument(
        "execution_id",
        help="Execution ID or full execution name",
    )


def handle(ctx: dict[str, Any]) -> int:
    """Handle workflow command.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]

    # Validate configuration
    try:
        require_config(ctx)
    except ConfigError as e:
        error(str(e))
        return 2

    if not args.workflow_subcommand:
        # Print help instead of error message
        if hasattr(args, "_workflow_parser"):
            args._workflow_parser.print_help()
        else:
            error("No subcommand specified. Use 'epycloud workflow --help'")
        return 1

    # Route to subcommand handler
    if args.workflow_subcommand == "list":
        return _handle_list(ctx)
    elif args.workflow_subcommand == "describe":
        return _handle_describe(ctx)
    elif args.workflow_subcommand == "logs":
        return _handle_logs(ctx)
    elif args.workflow_subcommand == "cancel":
        return _handle_cancel(ctx)
    elif args.workflow_subcommand == "retry":
        return _handle_retry(ctx)
    else:
        error(f"Unknown subcommand: {args.workflow_subcommand}")
        return 1


def _handle_list(ctx: dict[str, Any]) -> int:
    """Handle workflow list command.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    config = ctx["config"]
    verbose = ctx["verbose"]

    # Get config values
    google_cloud_config = config.get("google_cloud", {})
    project_id = google_cloud_config.get("project_id")
    region = google_cloud_config.get("region", "us-central1")

    if not project_id:
        error("google_cloud.project_id not configured")
        return 2

    # Get workflow name (from terraform)
    workflow_name = "epymodelingsuite-pipeline"

    # Build API URL
    list_url = (
        f"https://workflowexecutions.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/workflows/{workflow_name}/executions"
    )

    # Add query parameters
    params = []
    if args.limit:
        params.append(f"pageSize={args.limit}")
    if args.status:
        # Note: API filter syntax requires quotes: state="SUCCEEDED" or state="FAILED"
        params.append(f'filter=state="{args.status}"')

    if params:
        list_url += "?" + "&".join(params)

    # Get auth token
    try:
        token = get_gcloud_access_token(verbose)
    except Exception as e:
        error(f"Failed to get access token: {e}")
        return 1

    # Make API request
    try:
        response = requests.get(
            list_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        result = response.json()
        executions = result.get("executions", [])

        # Apply time-based filter first (doesn't need arguments)
        if args.since:
            cutoff_time = parse_since_time(args.since)
            if cutoff_time:
                executions = [
                    e for e in executions if _parse_timestamp(e.get("startTime", "")) > cutoff_time
                ]

        if not executions:
            info("No workflow executions found")
            return 0

        # Enrich executions with arguments (list endpoint doesn't include them)
        executions = _enrich_executions_with_arguments(
            executions, project_id, region, token, verbose
        )

        # Apply exp_id filter after enrichment (needs arguments)
        if args.exp_id:
            executions = [
                e
                for e in executions
                if args.exp_id in e.get("argument", e.get("workflowRevisionId", ""))
            ]

        if not executions:
            info("No workflow executions found")
            return 0

        # Display executions
        _display_execution_list(executions, region)
        return 0

    except requests.HTTPError as e:
        error(f"Failed to list executions: HTTP {e.response.status_code}")
        if verbose and e.response is not None:
            print(e.response.text, file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Failed to list executions: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _handle_describe(ctx: dict[str, Any]) -> int:
    """Handle workflow describe command.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    config = ctx["config"]
    verbose = ctx["verbose"]

    # Get config values
    google_cloud_config = config.get("google_cloud", {})
    project_id = google_cloud_config.get("project_id")
    region = google_cloud_config.get("region", "us-central1")

    if not project_id:
        error("google_cloud.project_id not configured")
        return 2

    # Parse execution ID
    execution_name = _parse_execution_name(
        args.execution_id, project_id, region, "epymodelingsuite-pipeline"
    )

    # Build API URL
    describe_url = f"https://workflowexecutions.googleapis.com/v1/{execution_name}"

    # Get auth token
    try:
        token = get_gcloud_access_token(verbose)
    except Exception as e:
        error(f"Failed to get access token: {e}")
        return 1

    # Make API request
    try:
        response = requests.get(
            describe_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        execution = response.json()
        _display_execution_details(execution)
        return 0

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            error(f"Execution not found: {args.execution_id}")
        else:
            status_code = e.response.status_code if e.response else "unknown"
            error(f"Failed to describe execution: HTTP {status_code}")
        if verbose and e.response is not None:
            print(e.response.text, file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Failed to describe execution: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _handle_logs(ctx: dict[str, Any]) -> int:
    """Handle workflow logs command.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    config = ctx["config"]
    verbose = ctx["verbose"]

    # Get config values
    google_cloud_config = config.get("google_cloud", {})
    project_id = google_cloud_config.get("project_id")
    region = google_cloud_config.get("region", "us-central1")

    if not project_id:
        error("google_cloud.project_id not configured")
        return 2

    # Parse execution ID
    execution_id = args.execution_id
    if "/" in execution_id:
        # Extract just the ID from full path
        execution_id = execution_id.split("/")[-1]

    info(f"Fetching logs for execution: {execution_id}")

    # Build gcloud logging query
    # Logs from Cloud Workflows are in Cloud Logging
    filter_parts = [
        'resource.type="workflows.googleapis.com/Workflow"',
        'resource.labels.workflow_id="epymodelingsuite-pipeline"',
        f'resource.labels.location="{region}"',
        f'labels.execution_id="{execution_id}"',
    ]

    log_filter = " AND ".join(filter_parts)

    # Build gcloud command
    cmd = [
        "gcloud",
        "logging",
        "read",
        log_filter,
        "--project",
        project_id,
        "--limit",
        str(args.tail),
        "--format",
        "json",
    ]

    if args.follow:
        # For follow mode, we need to continuously poll
        return _stream_logs(project_id, execution_id, region, verbose)

    # One-time log fetch
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            warning("No logs found for this execution")
            info("Note: Workflow logs may not be available immediately after submission")
            return 0

        # Parse and display logs
        logs = json.loads(result.stdout)
        _display_logs(logs)
        return 0

    except subprocess.CalledProcessError as e:
        error("Failed to fetch logs")
        if verbose:
            print(e.stderr, file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Failed to fetch logs: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _handle_cancel(ctx: dict[str, Any]) -> int:
    """Handle workflow cancel command.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    config = ctx["config"]
    verbose = ctx["verbose"]
    dry_run = ctx["dry_run"]

    # Get config values
    google_cloud_config = config.get("google_cloud", {})
    project_id = google_cloud_config.get("project_id")
    region = google_cloud_config.get("region", "us-central1")

    if not project_id:
        error("google_cloud.project_id not configured")
        return 2

    # Parse execution ID
    execution_name = _parse_execution_name(
        args.execution_id, project_id, region, "epymodelingsuite-pipeline"
    )

    info(f"Cancelling execution: {args.execution_id}")

    if dry_run:
        info(f"Would cancel: {execution_name}")
        return 0

    # Build API URL
    cancel_url = f"https://workflowexecutions.googleapis.com/v1/{execution_name}:cancel"

    # Get auth token
    try:
        token = get_gcloud_access_token(verbose)
    except Exception as e:
        error(f"Failed to get access token: {e}")
        return 1

    # Make API request
    try:
        response = requests.post(
            cancel_url,
            json={},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        success(f"Execution cancelled: {args.execution_id}")
        return 0

    except requests.HTTPError as e:
        if e.response is not None:
            if e.response.status_code == 404:
                error(f"Execution not found: {args.execution_id}")
            elif e.response.status_code == 400:
                warning("Execution may already be completed or cancelled")
            else:
                error(f"Failed to cancel execution: HTTP {e.response.status_code}")
            if verbose:
                print(e.response.text, file=sys.stderr)
        else:
            error("Failed to cancel execution: No response")
        return 1
    except Exception as e:
        error(f"Failed to cancel execution: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _handle_retry(ctx: dict[str, Any]) -> int:
    """Handle workflow retry command.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    config = ctx["config"]
    verbose = ctx["verbose"]
    dry_run = ctx["dry_run"]

    # Get config values
    google_cloud_config = config.get("google_cloud", {})
    project_id = google_cloud_config.get("project_id")
    region = google_cloud_config.get("region", "us-central1")

    if not project_id:
        error("google_cloud.project_id not configured")
        return 2

    # Parse execution ID
    execution_name = _parse_execution_name(
        args.execution_id, project_id, region, "epymodelingsuite-pipeline"
    )

    info(f"Fetching execution details: {args.execution_id}")

    # First, get the original execution details
    describe_url = f"https://workflowexecutions.googleapis.com/v1/{execution_name}"

    try:
        token = get_gcloud_access_token(verbose)
    except Exception as e:
        error(f"Failed to get access token: {e}")
        return 1

    try:
        response = requests.get(
            describe_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        execution = response.json()

        # Extract original argument
        argument_str = execution.get("argument", "{}")
        try:
            original_arg = json.loads(argument_str)
        except json.JSONDecodeError:
            original_arg = {}

        info("Retrying execution with same parameters:")
        print(json.dumps(original_arg, indent=2))

        if dry_run:
            info("Would resubmit workflow with above parameters")
            return 0

        # Submit new execution with same arguments
        submit_url = (
            f"https://workflowexecutions.googleapis.com/v1/"
            f"projects/{project_id}/locations/{region}/workflows/epymodelingsuite-pipeline/executions"
        )

        request_body = {"argument": json.dumps(original_arg)}

        response = requests.post(
            submit_url,
            json=request_body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        result = response.json()
        new_execution_name = result.get("name", "")
        new_execution_id = new_execution_name.split("/")[-1] if new_execution_name else ""

        success(f"New execution submitted: {new_execution_id}")
        info(f"Monitor with: epycloud workflow describe {new_execution_id}")
        return 0

    except requests.HTTPError as e:
        if e.response is not None:
            if e.response.status_code == 404:
                error(f"Execution not found: {args.execution_id}")
            else:
                error(f"Failed to retry execution: HTTP {e.response.status_code}")
            if verbose:
                print(e.response.text, file=sys.stderr)
        else:
            error("Failed to retry execution: No response")
        return 1
    except Exception as e:
        error(f"Failed to retry execution: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


# ========== Helper Functions ==========


def _enrich_executions_with_arguments(
    executions: list[dict[str, Any]],
    project_id: str,
    region: str,
    token: str,
    verbose: bool,
) -> list[dict[str, Any]]:
    """Enrich executions with argument data from describe endpoint.

    The list endpoint doesn't include arguments, so we need to fetch them
    individually for each execution.

    Parameters
    ----------
    executions : list[dict[str, Any]]
        List of execution objects from list endpoint
    project_id : str
        GCP project ID
    region : str
        GCP region
    token : str
        OAuth access token
    verbose : bool
        Enable verbose output

    Returns
    -------
    list[dict[str, Any]]
        List of executions enriched with argument field
    """
    enriched = []

    # Use session for connection pooling across multiple requests
    with requests.Session() as session:
        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )

        for execution in executions:
            name = execution.get("name", "")
            if not name:
                enriched.append(execution)
                continue

            # Fetch full execution details
            try:
                describe_url = f"https://workflowexecutions.googleapis.com/v1/{name}"
                response = session.get(describe_url)
                response.raise_for_status()
                full_execution = response.json()
                # Merge argument into original execution
                if "argument" in full_execution:
                    execution["argument"] = full_execution["argument"]
                enriched.append(execution)

            except Exception as e:
                if verbose:
                    warning(f"Failed to fetch details for {name}: {e}")
                enriched.append(execution)

    return enriched


def _parse_execution_name(
    execution_id: str, project_id: str, region: str, workflow_name: str
) -> str:
    """Parse execution ID to full execution name.

    Parameters
    ----------
    execution_id : str
        Execution ID or full name
    project_id : str
        GCP project ID
    region : str
        GCP region
    workflow_name : str
        Workflow name

    Returns
    -------
    str
        Full execution name
    """
    if execution_id.startswith("projects/"):
        return execution_id

    # Build full name
    return (
        f"projects/{project_id}/locations/{region}/"
        f"workflows/{workflow_name}/executions/{execution_id}"
    )


def _parse_timestamp(timestamp: str) -> datetime:
    """Parse ISO 8601 timestamp.

    Parameters
    ----------
    timestamp : str
        ISO 8601 timestamp string

    Returns
    -------
    datetime
        Datetime object
    """
    try:
        # Handle different timestamp formats
        if timestamp.endswith("Z"):
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return datetime.fromisoformat(timestamp)
    except (ValueError, AttributeError):
        return datetime.min.replace(tzinfo=UTC)


def _display_execution_list(executions: list[dict[str, Any]], region: str) -> None:
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


def _display_execution_details(execution: dict[str, Any]) -> None:
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


def _display_logs(logs: list[dict[str, Any]]) -> None:
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


def _stream_logs(project_id: str, execution_id: str, region: str, verbose: bool) -> int:
    """Stream logs in follow mode.

    Parameters
    ----------
    project_id : str
        GCP project ID
    execution_id : str
        Execution ID
    region : str
        GCP region
    verbose : bool
        Verbose output

    Returns
    -------
    int
        Exit code
    """
    info("Streaming logs (Ctrl+C to stop)...")
    print()

    last_timestamp = None
    poll_interval = 5  # seconds

    try:
        while True:
            # Build filter
            filter_parts = [
                'resource.type="workflows.googleapis.com/Workflow"',
                'resource.labels.workflow_id="epymodelingsuite-pipeline"',
                f'resource.labels.location="{region}"',
                f'labels.execution_id="{execution_id}"',
            ]

            if last_timestamp:
                filter_parts.append(f'timestamp>"{last_timestamp}"')

            log_filter = " AND ".join(filter_parts)

            # Fetch logs
            cmd = [
                "gcloud",
                "logging",
                "read",
                log_filter,
                "--project",
                project_id,
                "--limit",
                "100",
                "--format",
                "json",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                logs = json.loads(result.stdout)

                # Display new logs
                for entry in reversed(logs):
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

                    # Update last timestamp
                    if timestamp:
                        last_timestamp = timestamp

            # Wait before next poll
            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print()
        info("Stopped streaming logs")
        return 0
    except Exception as e:
        error(f"Failed to stream logs: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1
