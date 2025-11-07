"""Workflow command for managing Cloud Workflows executions."""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import (
    get_gcloud_access_token,
    require_config,
)
from epycloud.lib.formatters import (
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

    Args:
        subparsers: Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "workflow",
        help="Manage Cloud Workflows executions",
        description="List, describe, monitor, and manage workflow executions",
    )

    # Create subcommands
    workflow_subparsers = parser.add_subparsers(
        dest="workflow_subcommand", help="Workflow operation"
    )

    # ========== workflow list ==========
    list_parser = workflow_subparsers.add_parser(
        "list",
        help="List workflow executions",
    )

    list_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of executions to show (default: 10)",
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

    Args:
        ctx: Command context

    Returns:
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

    Args:
        ctx: Command context

    Returns:
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
        # Note: API filter syntax is: state=SUCCEEDED or state=FAILED
        params.append(f"filter=state={args.status}")

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
        req = urllib.request.Request(
            list_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            executions = result.get("executions", [])

            # Apply additional filters
            if args.exp_id:
                executions = [
                    e
                    for e in executions
                    if args.exp_id in e.get("argument", e.get("workflowRevisionId", ""))
                ]

            if args.since:
                cutoff_time = parse_since_time(args.since)
                if cutoff_time:
                    executions = [
                        e
                        for e in executions
                        if _parse_timestamp(e.get("startTime", "")) > cutoff_time
                    ]

            if not executions:
                info("No workflow executions found")
                return 0

            # Display executions
            _display_execution_list(executions, region)
            return 0

    except urllib.error.HTTPError as e:
        error(f"Failed to list executions: HTTP {e.code}")
        if verbose:
            print(e.read().decode("utf-8"), file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Failed to list executions: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _handle_describe(ctx: dict[str, Any]) -> int:
    """Handle workflow describe command.

    Args:
        ctx: Command context

    Returns:
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
        req = urllib.request.Request(
            describe_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req) as response:
            execution = json.loads(response.read().decode("utf-8"))
            _display_execution_details(execution)
            return 0

    except urllib.error.HTTPError as e:
        if e.code == 404:
            error(f"Execution not found: {args.execution_id}")
        else:
            error(f"Failed to describe execution: HTTP {e.code}")
        if verbose:
            print(e.read().decode("utf-8"), file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Failed to describe execution: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _handle_logs(ctx: dict[str, Any]) -> int:
    """Handle workflow logs command.

    Args:
        ctx: Command context

    Returns:
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

    Args:
        ctx: Command context

    Returns:
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
        req = urllib.request.Request(
            cancel_url,
            data=b"{}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req):
            success(f"Execution cancelled: {args.execution_id}")
            return 0

    except urllib.error.HTTPError as e:
        if e.code == 404:
            error(f"Execution not found: {args.execution_id}")
        elif e.code == 400:
            warning("Execution may already be completed or cancelled")
        else:
            error(f"Failed to cancel execution: HTTP {e.code}")
        if verbose:
            print(e.read().decode("utf-8"), file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Failed to cancel execution: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _handle_retry(ctx: dict[str, Any]) -> int:
    """Handle workflow retry command.

    Args:
        ctx: Command context

    Returns:
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
        req = urllib.request.Request(
            describe_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req) as response:
            execution = json.loads(response.read().decode("utf-8"))

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

            req = urllib.request.Request(
                submit_url,
                data=json.dumps(request_body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                new_execution_name = result.get("name", "")
                new_execution_id = new_execution_name.split("/")[-1] if new_execution_name else ""

                success(f"New execution submitted: {new_execution_id}")
                info(f"Monitor with: epycloud workflow describe {new_execution_id}")
                return 0

    except urllib.error.HTTPError as e:
        if e.code == 404:
            error(f"Execution not found: {args.execution_id}")
        else:
            error(f"Failed to retry execution: HTTP {e.code}")
        if verbose:
            print(e.read().decode("utf-8"), file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Failed to retry execution: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


# ========== Helper Functions ==========


def _parse_execution_name(
    execution_id: str, project_id: str, region: str, workflow_name: str
) -> str:
    """Parse execution ID to full execution name.

    Args:
        execution_id: Execution ID or full name
        project_id: GCP project ID
        region: GCP region
        workflow_name: Workflow name

    Returns:
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

    Args:
        timestamp: ISO 8601 timestamp string

    Returns:
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

    Args:
        executions: List of execution objects
        region: GCP region
    """
    print()
    print(f"{'EXECUTION ID':<40} {'STATUS':<12} {'START TIME':<20} {'EXP_ID':<20}")
    print("-" * 100)

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

        # Color code status
        status_display = format_status(state, "workflow")

        print(f"{execution_id:<40} {status_display:<20} {start_time_str:<20} {exp_id:<20}")

    print()
    info(f"Total: {len(executions)} execution(s)")
    print()


def _display_execution_details(execution: dict[str, Any]) -> None:
    """Display detailed execution information.

    Args:
        execution: Execution object
    """
    name = execution.get("name", "")
    execution_id = name.split("/")[-1] if name else "unknown"

    print()
    print("=" * 80)
    print(f"WORKFLOW EXECUTION: {execution_id}")
    print("=" * 80)
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
    print("=" * 80)
    print()


def _display_logs(logs: list[dict[str, Any]]) -> None:
    """Display logs in readable format.

    Args:
        logs: List of log entries
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

    Args:
        project_id: GCP project ID
        execution_id: Execution ID
        region: GCP region
        verbose: Verbose output

    Returns:
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

                    print(f"[{time_str}] {severity_display}: {text_payload}")

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
