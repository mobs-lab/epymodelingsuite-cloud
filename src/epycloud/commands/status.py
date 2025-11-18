"""Status command for monitoring pipeline status."""

import argparse
import json
import subprocess
import time
from datetime import datetime
from typing import Any

import requests

from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import (
    get_gcloud_access_token,
    get_google_cloud_config,
    require_config,
)
from epycloud.lib.formatters import format_status, format_timestamp_full
from epycloud.lib.output import error, info, warning


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the status command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "status",
        help="Check pipeline status",
        description="Monitor active workflows and batch jobs",
    )

    parser.add_argument(
        "--exp-id",
        help="Filter by experiment ID",
    )

    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch mode (auto-refresh)",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Refresh interval in seconds (default: 10)",
    )


def handle(ctx: dict[str, Any]) -> int:
    """Handle status command.

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

    # Validate configuration
    try:
        require_config(ctx)
        gcloud_config = get_google_cloud_config(ctx)
        project_id = gcloud_config["project_id"]
        region = gcloud_config.get("region", "us-central1")
    except (ConfigError, KeyError) as e:
        error(str(e))
        return 2

    # Watch mode
    if args.watch:
        return _watch_status(
            project_id=project_id,
            region=region,
            exp_id=args.exp_id,
            interval=args.interval,
            verbose=verbose,
        )

    # One-time status check
    return _show_status(
        project_id=project_id,
        region=region,
        exp_id=args.exp_id,
        verbose=verbose,
    )


def _show_status(
    project_id: str,
    region: str,
    exp_id: str | None,
    verbose: bool,
) -> int:
    """Show current status.

    Parameters
    ----------
    project_id : str
        GCP project ID
    region : str
        GCP region
    exp_id : str | None
        Optional experiment ID filter
    verbose : bool
        Verbose output

    Returns
    -------
    int
        Exit code
    """
    try:
        # Fetch active workflows
        workflows = _fetch_active_workflows(
            project_id=project_id,
            region=region,
            exp_id=exp_id,
            verbose=verbose,
        )

        # Fetch active batch jobs
        jobs = _fetch_active_batch_jobs(
            project_id=project_id,
            region=region,
            exp_id=exp_id,
            verbose=verbose,
        )

        # Display status
        _display_status(workflows, jobs, exp_id)

        return 0

    except Exception as e:
        error(f"Failed to fetch status: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _watch_status(
    project_id: str,
    region: str,
    exp_id: str | None,
    interval: int,
    verbose: bool,
) -> int:
    """Watch status with auto-refresh.

    Parameters
    ----------
    project_id : str
        GCP project ID
    region : str
        GCP region
    exp_id : str | None
        Optional experiment ID filter
    interval : int
        Refresh interval in seconds
    verbose : bool
        Verbose output

    Returns
    -------
    int
        Exit code
    """
    info(f"Watching pipeline status (refreshing every {interval}s, Ctrl+C to stop)...")
    print()

    try:
        while True:
            # Clear screen
            print("\033[2J\033[H", end="")

            # Fetch and display status
            try:
                workflows = _fetch_active_workflows(
                    project_id=project_id,
                    region=region,
                    exp_id=exp_id,
                    verbose=verbose,
                )

                jobs = _fetch_active_batch_jobs(
                    project_id=project_id,
                    region=region,
                    exp_id=exp_id,
                    verbose=verbose,
                )

                _display_status(workflows, jobs, exp_id)

                # Show refresh time
                now = format_timestamp_full(datetime.now().isoformat())
                print(f"Last updated: {now} (refreshing every {interval}s)")

            except Exception as e:
                warning(f"Failed to refresh: {e}")

            # Wait before next refresh
            time.sleep(interval)

    except KeyboardInterrupt:
        print()
        info("Stopped watching")
        return 0


def _fetch_active_workflows(
    project_id: str,
    region: str,
    exp_id: str | None,
    verbose: bool,
) -> list[dict[str, Any]]:
    """Fetch active workflow executions.

    Parameters
    ----------
    project_id : str
        GCP project ID
    region : str
        GCP region
    exp_id : str | None
        Optional experiment ID filter
    verbose : bool
        Verbose output

    Returns
    -------
    list[dict[str, Any]]
        List of active workflow executions
    """
    workflow_name = "epymodelingsuite-pipeline"
    list_url = (
        f"https://workflowexecutions.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/workflows/{workflow_name}/executions"
        f'?pageSize=20&filter=state="ACTIVE"&view=FULL'
    )

    try:
        # Get auth token
        token = _get_access_token(verbose)

        # Make API request
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

        # Filter by exp_id if provided
        if exp_id:
            executions = [e for e in executions if exp_id in e.get("argument", "")]

        return executions

    except Exception as e:
        if verbose:
            warning(f"Failed to fetch workflows: {e}")
        return []


def _fetch_active_batch_jobs(
    project_id: str,
    region: str,
    exp_id: str | None,
    verbose: bool,
) -> list[dict[str, Any]]:
    """Fetch active Cloud Batch jobs.

    Parameters
    ----------
    project_id : str
        GCP project ID
    region : str
        GCP region
    exp_id : str | None
        Optional experiment ID filter
    verbose : bool
        Verbose output

    Returns
    -------
    list[dict[str, Any]]
        List of active batch jobs
    """
    try:
        # Build gcloud command
        cmd = [
            "gcloud",
            "batch",
            "jobs",
            "list",
            f"--project={project_id}",
            f"--location={region}",
            "--format=json",
            "--filter=state:RUNNING OR state:QUEUED OR state:SCHEDULED",
        ]

        if exp_id:
            cmd.append(f"--filter=labels.exp_id={exp_id}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            return []

        jobs = json.loads(result.stdout)
        return jobs

    except Exception as e:
        if verbose:
            warning(f"Failed to fetch batch jobs: {e}")
        return []


def _get_access_token(verbose: bool = False) -> str:
    """Get GCP access token using gcloud.

    Parameters
    ----------
    verbose : bool
        Verbose output

    Returns
    -------
    str
        Access token

    Raises
    ------
    CloudAPIError
        If unable to get token
    """
    return get_gcloud_access_token(verbose)


def _display_status(
    workflows: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    exp_id_filter: str | None,
) -> None:
    """Display pipeline status.

    Parameters
    ----------
    workflows : list[dict[str, Any]]
        List of active workflow executions
    jobs : list[dict[str, Any]]
        List of active batch jobs
    exp_id_filter : str | None
        Optional experiment ID filter for display
    """
    print()
    if exp_id_filter:
        print(f"Pipeline Status: {exp_id_filter}")
    else:
        print("Pipeline Status")
    print("=" * 100)
    print()

    # Display active workflows
    if workflows:
        print("Active Workflows:")
        print()
        print(f"{'EXECUTION ID':<40} {'EXP_ID':<20} {'START TIME':<20}")
        print("-" * 100)

        for workflow in workflows:
            name = workflow.get("name", "")
            execution_id = name.split("/")[-1] if name else "unknown"

            # Extract exp_id from argument
            # Note: The list API returns minimal argument data.
            # We need to check labels or fetch full details for exp_id.
            argument_str = workflow.get("argument", "{}")
            exp_id = "unknown"
            try:
                arg = json.loads(argument_str)
                exp_id = arg.get("exp_id", "unknown")
            except json.JSONDecodeError:
                pass

            # If not found in argument (common in list responses), try labels
            if exp_id == "unknown":
                labels = workflow.get("labels", {})
                exp_id = labels.get("exp_id", "unknown")

            # Format start time
            start_time = workflow.get("startTime", "")
            if start_time:
                start_time_str = format_timestamp_full(start_time)
            else:
                start_time_str = "unknown"

            print(f"{execution_id:<40} {exp_id:<20} {start_time_str:<20}")

        print()
    else:
        info("No active workflows")
        print()

    # Display active batch jobs
    if jobs:
        print("Active Batch Jobs:")
        print()
        print(f"{'JOB NAME':<50} {'STAGE':<8} {'STATUS':<12} {'TASKS':<15}")
        print("-" * 100)

        for job in jobs:
            job_name = job.get("name", "").split("/")[-1]
            status = job.get("status", {})
            state = status.get("state", "UNKNOWN")

            # Get labels
            labels = job.get("labels", {})
            stage = labels.get("stage", "unknown")

            # Get task counts
            task_groups = status.get("taskGroups", {})
            if task_groups:
                # Get first task group
                first_group = list(task_groups.values())[0] if task_groups else {}
                task_counts = first_group.get("counts", {})

                succeeded = task_counts.get("succeeded", 0)
                failed = task_counts.get("failed", 0)
                running = task_counts.get("running", 0)

                # Calculate total tasks
                total = sum(task_counts.values()) if task_counts else 0
                completed = succeeded + failed

                if total > 0:
                    tasks_str = f"{completed}/{total}"
                else:
                    tasks_str = f"{running} running"
            else:
                tasks_str = "N/A"

            # Color code status
            status_display = format_status(state, "batch")

            print(f"{job_name:<50} {stage:<8} {status_display:<20} {tasks_str:<15}")

        print()
    else:
        info("No active batch jobs")
        print()

    # Summary
    total_active = len(workflows) + len(jobs)
    if total_active == 0:
        print("All pipelines idle")
    else:
        print(f"Total active: {len(workflows)} workflow(s), {len(jobs)} batch job(s)")

    print()
