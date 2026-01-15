"""Status operations and utilities."""

import json
import subprocess
from typing import Any

import requests

from epycloud.lib.command_helpers import get_gcloud_access_token
from epycloud.lib.formatters import format_status, format_timestamp_local
from epycloud.lib.output import section_header, supports_color, warning


def extract_image_tag(image_uri: str) -> str:
    """Extract tag from Docker image URI.

    Parameters
    ----------
    image_uri : str
        Full image URI (e.g., "us-central1-docker.pkg.dev/proj/repo/img:tag")

    Returns
    -------
    str
        Image tag, digest prefix, or "latest" if no tag specified
    """
    if not image_uri:
        return "unknown"

    if "@sha256:" in image_uri:
        # Digest reference - show first 7 chars of hash (like git)
        digest = image_uri.split("@sha256:")[-1]
        return f"sha256:{digest[:7]}"
    elif ":" in image_uri.split("/")[-1]:
        # Has explicit tag
        return image_uri.split(":")[-1]
    else:
        # No tag = implicit latest
        return "latest"


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
    base_url = (
        f"https://workflowexecutions.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/workflows/{workflow_name}/executions"
    )

    try:
        # Get auth token
        token = get_gcloud_access_token(verbose)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Fetch all pages of results
        all_executions: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            # Build URL with pagination
            url = f'{base_url}?pageSize=30&filter=state="ACTIVE"&view=FULL'
            if page_token:
                url += f"&pageToken={page_token}"

            response = requests.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()

            executions = result.get("executions", [])
            all_executions.extend(executions)

            # Check for next page
            page_token = result.get("nextPageToken")
            if not page_token:
                break

        # Filter by exp_id if provided
        if exp_id:
            all_executions = [
                e for e in all_executions if exp_id in e.get("argument", "")
            ]

        # Sort by exp_id
        def get_workflow_exp_id(workflow: dict[str, Any]) -> str:
            try:
                arg = json.loads(workflow.get("argument", "{}"))
                return arg.get("exp_id", "")
            except json.JSONDecodeError:
                return ""

        all_executions.sort(key=get_workflow_exp_id)

        return all_executions

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

        # Sort by exp_id
        def get_job_exp_id(job: dict[str, Any]) -> str:
            task_groups = job.get("taskGroups", [])
            if task_groups:
                task_spec = task_groups[0].get("taskSpec", {})
                env_vars = task_spec.get("environment", {}).get("variables", {})
                return env_vars.get("EXP_ID", job.get("labels", {}).get("exp_id", ""))
            return job.get("labels", {}).get("exp_id", "")

        jobs.sort(key=get_job_exp_id)

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

        print("-" * 135)
        print(f"{'EXP_ID':<60} {'EXECUTION ID':<45} {'START TIME':<24}")
        print("-" * 135)

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

            # Truncate exp_id if too long (keep first 57 chars + "...")
            if len(exp_id) > 60:
                exp_id = exp_id[:57] + "..."

            # Format start time (local time with timezone)
            start_time = workflow.get("startTime", "")
            if start_time:
                start_time_str = format_timestamp_local(start_time)
            else:
                start_time_str = "unknown"

            print(f"{exp_id:<60} {execution_id:<45} {start_time_str:<24}")

        print()

    # Display active batch jobs
    if jobs:
        section_header("Active batch jobs")

        print("-" * 135)
        print(f"{'EXP_ID':<60} {'JOB NAME':<25} {'STAGE':<8} {'IMAGE TAG':<15} {'STATUS':<12} {'TASKS':<7}")
        print("-" * 135)

        for job in jobs:
            job_name = job.get("name", "").split("/")[-1]
            # Truncate job_name if too long
            if len(job_name) > 25:
                job_name = job_name[:22] + "..."
            status = job.get("status", {})
            state = status.get("state", "UNKNOWN")

            # Get labels
            labels = job.get("labels", {})
            stage = labels.get("stage", "unknown")

            # Get exp_id and image_uri from task spec
            task_groups_list = job.get("taskGroups", [])
            exp_id = "unknown"
            image_tag = "unknown"
            if task_groups_list:
                task_spec = task_groups_list[0].get("taskSpec", {})
                env_vars = task_spec.get("environment", {}).get("variables", {})
                exp_id = env_vars.get("EXP_ID", labels.get("exp_id", "unknown"))

                # Extract image tag from container config
                runnables = task_spec.get("runnables", [])
                if runnables:
                    image_uri = runnables[0].get("container", {}).get("imageUri", "")
                    image_tag = extract_image_tag(image_uri)

            # Truncate exp_id if too long (keep first 57 chars + "...")
            if len(exp_id) > 60:
                exp_id = exp_id[:57] + "..."

            # Truncate image_tag if too long
            if len(image_tag) > 15:
                image_tag = image_tag[:12] + "..."

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

            print(f"{exp_id:<60} {job_name:<25} {stage:<8} {image_tag:<15} {status_display} {tasks_str:<7}")

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
