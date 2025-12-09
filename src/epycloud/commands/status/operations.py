"""Status operations and utilities."""

import json
import subprocess
from typing import Any

import requests

from epycloud.lib.command_helpers import get_gcloud_access_token
from epycloud.lib.formatters import format_status, format_timestamp_full
from epycloud.lib.output import section_header, supports_color, warning


def fetch_active_workflows(
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
        token = get_gcloud_access_token(verbose)

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


def fetch_active_batch_jobs(
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
        # Build gcloud command filter
        # Note: Multiple state checks need parentheses for OR grouping
        state_filter = "(status.state:RUNNING OR status.state:QUEUED OR status.state:SCHEDULED)"

        if exp_id:
            # Sanitize exp_id for label filtering (must match what was set in job creation)
            from epycloud.lib.validation import sanitize_label_value

            exp_id_label = sanitize_label_value(exp_id)
            # Combine state filter with exp_id filter using AND
            filter_expr = f"{state_filter} AND labels.exp_id={exp_id_label}"
        else:
            filter_expr = state_filter

        cmd = [
            "gcloud",
            "batch",
            "jobs",
            "list",
            f"--project={project_id}",
            f"--location={region}",
            "--format=json",
            f"--filter={filter_expr}",
        ]

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


def display_status(
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
    # Display active workflows
    if workflows:
        print()  # Blank line before section
        section_header("Active workflows")

        print("-" * 120)
        print(f"{'EXECUTION ID':<40} {'EXP_ID':<40} {'START TIME':<37}")
        print("-" * 120)

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

            print(f"{execution_id:<40} {exp_id:<40} {start_time_str:<37}")

        print()

    # Display active batch jobs
    if jobs:
        section_header("Active batch jobs")

        print("-" * 120)
        print(f"{'JOB NAME':<40} {'EXP_ID':<40} {'STAGE':<8} {'STATUS':<12} {'TASKS':<15}")
        print("-" * 120)

        for job in jobs:
            job_name = job.get("name", "").split("/")[-1]
            status = job.get("status", {})
            state = status.get("state", "UNKNOWN")

            # Get labels
            labels = job.get("labels", {})
            stage = labels.get("stage", "unknown")

            # Get exp_id from environment variables (original, unsanitized)
            task_groups_list = job.get("taskGroups", [])
            exp_id = "unknown"
            if task_groups_list:
                task_spec = task_groups_list[0].get("taskSpec", {})
                env_vars = task_spec.get("environment", {}).get("variables", {})
                exp_id = env_vars.get("EXP_ID", labels.get("exp_id", "unknown"))

            # Get task counts
            task_groups = status.get("taskGroups", {})
            if task_groups:
                # Get first task group
                first_group = list(task_groups.values())[0] if task_groups else {}
                task_counts = first_group.get("counts", {})

                # Convert counts to integers (API may return strings)
                succeeded = int(task_counts.get("SUCCEEDED", 0))
                failed = int(task_counts.get("FAILED", 0))
                running = int(task_counts.get("RUNNING", 0))
                pending = int(task_counts.get("PENDING", 0))

                # Calculate total tasks
                total = succeeded + failed + running + pending
                completed = succeeded + failed

                if total > 0:
                    tasks_str = f"{completed}/{total}"
                else:
                    tasks_str = f"{running} running" if running > 0 else "pending"
            else:
                tasks_str = "N/A"

            # Color code status (pad before coloring to avoid ANSI escape code width issues)
            status_padded = f"{state:<12}"
            status_display = format_status(status_padded, "batch")

            print(f"{job_name:<40} {exp_id:<40} {stage:<8} {status_display} {tasks_str:<15}")

        print()

    # Summary
    total_active = len(workflows) + len(jobs)
    if total_active == 0:
        print()  # Blank line before
        if supports_color():
            print("\033[90mAll pipelines idle\033[0m")
        else:
            print("All pipelines idle")
        print()  # Blank line after
    else:
        print()  # Blank line before
        print(f"Total: {len(workflows)} workflow(s), {len(jobs)} batch job(s)")
        print()  # Blank line after
