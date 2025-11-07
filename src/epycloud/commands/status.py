"""Status command for monitoring pipeline status."""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

from epycloud.lib.output import error, info, warning


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the status command parser.

    Args:
        subparsers: Subparser action from main parser
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
    region = google_cloud_config.get("region", "us-central1")

    if not project_id:
        error("google_cloud.project_id not configured")
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

    Args:
        project_id: GCP project ID
        region: GCP region
        exp_id: Optional experiment ID filter
        verbose: Verbose output

    Returns:
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

    Args:
        project_id: GCP project ID
        region: GCP region
        exp_id: Optional experiment ID filter
        interval: Refresh interval in seconds
        verbose: Verbose output

    Returns:
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
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

    Args:
        project_id: GCP project ID
        region: GCP region
        exp_id: Optional experiment ID filter
        verbose: Verbose output

    Returns:
        List of active workflow executions
    """
    workflow_name = "epymodelingsuite-pipeline"
    list_url = (
        f"https://workflowexecutions.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/workflows/{workflow_name}/executions"
        f"?pageSize=20&filter=state=ACTIVE"
    )

    try:
        # Get auth token
        token = _get_access_token(verbose)

        # Make API request
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

    Args:
        project_id: GCP project ID
        region: GCP region
        exp_id: Optional experiment ID filter
        verbose: Verbose output

    Returns:
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

    Args:
        verbose: Verbose output

    Returns:
        Access token

    Raises:
        Exception: If unable to get token
    """
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if verbose:
            print(e.stderr, file=sys.stderr)
        raise Exception("Failed to get access token")


def _display_status(
    workflows: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    exp_id_filter: str | None,
) -> None:
    """Display pipeline status.

    Args:
        workflows: List of active workflow executions
        jobs: List of active batch jobs
        exp_id_filter: Optional experiment ID filter for display
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
            argument_str = workflow.get("argument", "{}")
            exp_id = "unknown"
            try:
                arg = json.loads(argument_str)
                exp_id = arg.get("exp_id", "unknown")
            except json.JSONDecodeError:
                pass

            # Format start time
            start_time = workflow.get("startTime", "")
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    start_time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, IndexError):
                    start_time_str = start_time[:19]
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
            if state == "RUNNING":
                status_display = f"\033[33m{state}\033[0m"
            elif state == "SUCCEEDED":
                status_display = f"\033[32m{state}\033[0m"
            elif state == "FAILED":
                status_display = f"\033[31m{state}\033[0m"
            else:
                status_display = state

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
