"""Logs command for viewing pipeline logs."""

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from typing import Any

from epycloud.lib.output import error, info, warning


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the logs command parser.

    Args:
        subparsers: Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "logs",
        help="View pipeline logs",
        description="View logs from Cloud Batch jobs and workflow executions",
    )

    parser.add_argument(
        "--exp-id",
        help="Experiment ID (required)",
        required=True,
    )

    parser.add_argument(
        "--run-id",
        help="Run ID (optional, shows all runs if not specified)",
    )

    parser.add_argument(
        "--stage",
        choices=["A", "B", "C", "builder", "runner", "output"],
        help="Stage to view logs for: A|B|C|builder|runner|output",
    )

    parser.add_argument(
        "--task-index",
        type=int,
        help="Task index for stage B (default: all tasks)",
    )

    parser.add_argument(
        "--follow",
        "-f",
        action="store_true",
        help="Follow mode (stream logs)",
    )

    parser.add_argument(
        "--tail",
        type=int,
        default=100,
        help="Show last N lines (default: 100)",
    )

    parser.add_argument(
        "--since",
        help="Show logs since (e.g., 1h, 30m, 24h)",
    )

    parser.add_argument(
        "--level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Filter by log level",
    )


def handle(ctx: dict[str, Any]) -> int:
    """Handle logs command.

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    args = ctx["args"]
    config = ctx["config"]
    verbose = ctx["verbose"]

    if not config:
        error("Configuration not loaded. Run 'epycloud config init' first")
        return 2

    # Get config values
    google_cloud_config = config.get("google_cloud", {})
    project_id = google_cloud_config.get("project_id")

    if not project_id:
        error("google_cloud.project_id not configured")
        return 2

    exp_id = args.exp_id
    run_id = args.run_id
    stage = args.stage
    task_index = args.task_index

    # Normalize stage name
    if stage:
        stage = _normalize_stage_name(stage)

    # Build log filter
    filter_parts = []

    # Resource type: Cloud Batch jobs
    filter_parts.append('resource.type="batch.googleapis.com/Job"')

    # Labels
    filter_parts.append(f'labels.exp_id="{exp_id}"')

    if run_id:
        filter_parts.append(f'labels.run_id="{run_id}"')

    if stage:
        filter_parts.append(f'labels.stage="{stage}"')

    if task_index is not None:
        filter_parts.append(f'labels.batch.task_index="{task_index}"')

    # Severity level
    if args.level:
        filter_parts.append(f'severity="{args.level}"')

    # Timestamp filter
    if args.since:
        since_time = _parse_since_time(args.since)
        if since_time:
            filter_parts.append(f'timestamp>="{since_time}"')

    log_filter = " AND ".join(filter_parts)

    if verbose:
        info(f"Log filter: {log_filter}")
        print()

    # Follow mode
    if args.follow:
        return _stream_logs(
            project_id=project_id,
            log_filter=log_filter,
            verbose=verbose,
        )

    # One-time log fetch
    return _fetch_logs(
        project_id=project_id,
        log_filter=log_filter,
        tail=args.tail,
        verbose=verbose,
    )


def _fetch_logs(
    project_id: str,
    log_filter: str,
    tail: int,
    verbose: bool,
) -> int:
    """Fetch logs once.

    Args:
        project_id: GCP project ID
        log_filter: Cloud Logging filter
        tail: Number of lines to show
        verbose: Verbose output

    Returns:
        Exit code
    """
    info(f"Fetching last {tail} log entries...")
    print()

    try:
        # Build gcloud command
        cmd = [
            "gcloud",
            "logging",
            "read",
            log_filter,
            f"--project={project_id}",
            f"--limit={tail}",
            "--format=json",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            warning("No logs found")
            info("Note: Logs may not be available immediately after job submission")
            info("      Logs are retained for 30 days in Cloud Logging")
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


def _stream_logs(
    project_id: str,
    log_filter: str,
    verbose: bool,
) -> int:
    """Stream logs in follow mode.

    Args:
        project_id: GCP project ID
        log_filter: Cloud Logging filter
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
            # Add timestamp filter for new logs
            current_filter = log_filter
            if last_timestamp:
                current_filter += f' AND timestamp>"{last_timestamp}"'

            # Fetch logs
            cmd = [
                "gcloud",
                "logging",
                "read",
                current_filter,
                f"--project={project_id}",
                "--limit=100",
                "--format=json",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                logs = json.loads(result.stdout)

                # Display new logs (in chronological order)
                for entry in reversed(logs):
                    timestamp = entry.get("timestamp", "")
                    severity = entry.get("severity", "INFO")
                    text_payload = entry.get("textPayload", "")
                    json_payload = entry.get("jsonPayload", {})

                    # Format timestamp
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                            time_str = dt.strftime("%H:%M:%S")
                        except (ValueError, IndexError):
                            time_str = timestamp[11:19]
                    else:
                        time_str = ""

                    # Color code severity
                    if severity == "ERROR":
                        severity_display = f"\033[31m{severity}\033[0m"
                    elif severity == "WARNING":
                        severity_display = f"\033[33m{severity}\033[0m"
                    elif severity == "DEBUG":
                        severity_display = f"\033[90m{severity}\033[0m"
                    else:
                        severity_display = severity

                    # Display message
                    if text_payload:
                        print(f"[{time_str}] {severity_display}: {text_payload}")
                    elif json_payload:
                        message = json_payload.get("message", json.dumps(json_payload))
                        print(f"[{time_str}] {severity_display}: {message}")

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


def _display_logs(logs: list[dict[str, Any]]) -> None:
    """Display logs in readable format.

    Args:
        logs: List of log entries
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
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, IndexError):
                time_str = timestamp[:19]
        else:
            time_str = "unknown"

        # Color code severity
        if severity == "ERROR":
            severity_display = f"\033[31m{severity}\033[0m"
        elif severity == "WARNING":
            severity_display = f"\033[33m{severity}\033[0m"
        elif severity == "INFO":
            severity_display = f"\033[34m{severity}\033[0m"
        elif severity == "DEBUG":
            severity_display = f"\033[90m{severity}\033[0m"
        else:
            severity_display = severity

        # Build context string
        context_parts = []
        if stage:
            context_parts.append(f"stage={stage}")
        if task_index:
            context_parts.append(f"task={task_index}")

        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""

        # Display log entry
        print(f"[{time_str}] {severity_display}{context_str}")

        if text_payload:
            print(f"  {text_payload}")
        elif json_payload:
            # Try to format JSON payload nicely
            message = json_payload.get("message")
            if message:
                print(f"  {message}")
            else:
                print(f"  {json.dumps(json_payload, indent=2)}")

        print()


def _normalize_stage_name(stage: str) -> str:
    """Normalize stage name to letter format.

    Args:
        stage: Stage name (A/B/C or builder/runner/output)

    Returns:
        Normalized stage name (A/B/C)
    """
    stage_map = {
        "builder": "A",
        "runner": "B",
        "output": "C",
    }
    return stage_map.get(stage.lower(), stage.upper())


def _parse_since_time(since: str) -> str | None:
    """Parse since duration to ISO timestamp.

    Args:
        since: Duration string (e.g., 1h, 30m, 24h)

    Returns:
        ISO timestamp string or None if invalid
    """
    from datetime import datetime, timedelta

    try:
        if since.endswith("h"):
            hours = int(since[:-1])
            dt = datetime.now(UTC) - timedelta(hours=hours)
        elif since.endswith("m"):
            minutes = int(since[:-1])
            dt = datetime.now(UTC) - timedelta(minutes=minutes)
        elif since.endswith("d"):
            days = int(since[:-1])
            dt = datetime.now(UTC) - timedelta(days=days)
        else:
            return None

        return dt.isoformat()

    except ValueError:
        return None
