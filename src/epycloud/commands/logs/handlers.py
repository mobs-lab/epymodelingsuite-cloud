"""Handlers for logs command."""

import json
import subprocess
import sys
from typing import Any

from epycloud.exceptions import ConfigError, ValidationError
from epycloud.lib.command_helpers import get_google_cloud_config, require_config
from epycloud.lib.formatters import parse_since_time
from epycloud.lib.output import error, status, warning
from epycloud.lib.validation import (
    sanitize_label_value,
    validate_exp_id,
    validate_run_id,
    validate_stage_name,
)

from .display import display_logs
from .streaming import stream_logs


def handle(ctx: dict[str, Any]) -> int:
    """Handle logs command.

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
    verbose = ctx["verbose"]

    # Get and validate config
    try:
        require_config(ctx)
        gcloud_config = get_google_cloud_config(ctx)
        project_id = gcloud_config["project_id"]
    except (ConfigError, KeyError) as e:
        error(str(e))
        return 2

    # Require at least one of: exp_id, job_name, or execution_id
    if not args.exp_id and not args.job_name and not args.execution_id:
        error("At least one of --exp-id, --job-name, or --execution-id is required")
        return 1

    # Validate inputs
    try:
        exp_id = validate_exp_id(args.exp_id) if args.exp_id else None
        run_id = validate_run_id(args.run_id) if args.run_id else None
        stage = validate_stage_name(args.stage) if args.stage else None
    except ValidationError as e:
        error(str(e))
        return 1

    task_index = args.task_index

    # Normalize stage name
    if stage:
        stage = normalize_stage_name(stage)

    # Build log filter
    log_filter = build_log_filter(
        exp_id=exp_id,
        run_id=run_id,
        stage=stage,
        task_index=task_index,
        level=args.level,
        since=args.since,
        job_name=args.job_name,
        execution_id=args.execution_id,
    )

    if verbose:
        status(f"Log filter: {log_filter}")
        status("")

    # Follow mode
    if args.follow:
        return stream_logs(
            project_id=project_id,
            log_filter=log_filter,
            verbose=verbose,
        )

    # One-time log fetch
    return fetch_logs(
        project_id=project_id,
        log_filter=log_filter,
        tail=args.tail,
        verbose=verbose,
    )


def build_log_filter(
    exp_id: str | None,
    run_id: str | None,
    stage: str | None,
    task_index: int | None,
    level: str | None,
    since: str | None,
    job_name: str | None = None,
    execution_id: str | None = None,
) -> str:
    """Build Cloud Logging filter string.

    Parameters
    ----------
    exp_id : str | None
        Experiment ID (optional if job_name is provided)
    run_id : str | None
        Run ID (optional)
    stage : str | None
        Stage name (optional)
    task_index : int | None
        Task index (optional)
    level : str | None
        Log level (optional)
    since : str | None
        Since duration (optional)
    job_name : str | None
        Batch job name (optional, e.g., stage-b-003a2da6)
    execution_id : str | None
        Workflow execution ID (optional, filters all stages from that execution)

    Returns
    -------
    str
        Cloud Logging filter string
    """
    filter_parts = []

    # Resource type: Cloud Batch jobs
    filter_parts.append('resource.type="batch.googleapis.com/Job"')

    # Labels (must be sanitized to match what was set in job creation)
    if exp_id:
        exp_id_label = sanitize_label_value(exp_id)
        filter_parts.append(f'labels.exp_id="{exp_id_label}"')

    if run_id:
        run_id_label = sanitize_label_value(run_id)
        filter_parts.append(f'labels.run_id="{run_id_label}"')

    if stage:
        filter_parts.append(f'labels.stage="{stage}"')

    if task_index is not None:
        filter_parts.append(f'labels.batch.task_index="{task_index}"')

    # Job name filter (prefix match on batch job ID)
    # Job names like "stage-b-a50f0fb0" become UIDs like "stage-b-a50f0fb0-ae53b727-..."
    if job_name:
        filter_parts.append(f'labels.job_uid=~"^{job_name}"')

    # Execution ID filter (matches all stages from that execution)
    if execution_id:
        # Extract first 8 chars (uniqueId used in job names)
        unique_id = execution_id[:8]
        # Use regex to match all stages: stage-a-xxx, stage-b-xxx, stage-c-xxx
        filter_parts.append(f'labels.job_uid=~"^stage-.-{unique_id}"')

    # Severity level
    if level:
        filter_parts.append(f'severity="{level}"')

    # Timestamp filter
    if since:
        since_time = parse_since_time(since)
        if since_time:
            filter_parts.append(f'timestamp>="{since_time}"')

    return " AND ".join(filter_parts)


def fetch_logs(
    project_id: str,
    log_filter: str,
    tail: int,
    verbose: bool,
) -> int:
    """Fetch logs once.

    Parameters
    ----------
    project_id : str
        GCP project ID
    log_filter : str
        Cloud Logging filter
    tail : int
        Number of lines to show
    verbose : bool
        Verbose output

    Returns
    -------
    int
        Exit code
    """
    if tail == 0:
        status("Fetching all available log entries...")
    else:
        status(f"Fetching last {tail} log entries...")
    status("")

    try:
        # Build gcloud command
        cmd = [
            "gcloud",
            "logging",
            "read",
            log_filter,
            f"--project={project_id}",
            "--freshness=30d",  # Search logs from last 30 days (Cloud Logging retention)
            "--format=json",
        ]

        # Add limit only if not unlimited
        if tail > 0:
            cmd.insert(5, f"--limit={tail}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            warning("No logs found")
            status("Note: Logs may not be available immediately after job submission")
            status("      Logs are retained for 30 days in Cloud Logging")
            return 0

        # Parse and display logs
        logs = json.loads(result.stdout)
        display_logs(logs)

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


def normalize_stage_name(stage: str) -> str:
    """Normalize stage name to letter format.

    Parameters
    ----------
    stage : str
        Stage name (A/B/C or builder/runner/output)

    Returns
    -------
    str
        Normalized stage name (A/B/C)
    """
    stage_map = {
        "builder": "A",
        "runner": "B",
        "output": "C",
    }
    return stage_map.get(stage.lower(), stage.upper())
