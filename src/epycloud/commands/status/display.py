"""Render pipeline status tables and warnings."""

import json
from typing import Any

from epycloud.commands.status.operations import (
    ProvisioningAlert,
    extract_image_tag,
    extract_task_count,
    extract_task_counts,
    get_job_region,
)
from epycloud.lib.formatters import format_duration, format_status, format_timestamp_local
from epycloud.lib.output import section_header, supports_color


def display_status(
    workflows: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    exp_id_filter: str | None,
    recent_workflows: list[dict[str, Any]] | None = None,
    recent_jobs: list[dict[str, Any]] | None = None,
    provisioning_alerts: list[ProvisioningAlert] | None = None,
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
    recent_workflows : list[dict[str, Any]] | None
        List of recently completed workflow executions
    recent_jobs : list[dict[str, Any]] | None
        List of recently completed batch jobs
    provisioning_alerts : list[ProvisioningAlert] | None
        Underfilled active jobs to explain after the active jobs table
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

        header = (
            f"{'EXP_ID':<60} {'JOB NAME':<25} {'REGION':<13} {'MACHINE':<20} "
            f"{'IMAGE TAG':<15} {'STAGE':<8} {'STATUS':<12} {'TASKS':<9}"
        )
        print("-" * len(header))
        print(header)
        print("-" * len(header))

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
            batch_region = get_job_region(job)

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

            task_counts = extract_task_counts(job)
            completed = task_counts["SUCCEEDED"] + task_counts["FAILED"]
            task_count = extract_task_count(job)
            if task_count <= 0:
                task_count = sum(task_counts.values())
            tasks_str = f"{completed}/{task_count}" if task_count > 0 else "N/A"

            machine = ", ".join(
                instance.get("policy", {}).get("machineType") or "auto"
                for instance in job.get("allocationPolicy", {}).get("instances", [])
            ) or "auto"

            # Color code status (pad before coloring to avoid ANSI escape code width issues)
            status_padded = f"{state:<12}"
            status_display = format_status(status_padded, "batch")

            print(
                f"{exp_id:<60} {job_name:<25} {batch_region:<13} {machine:<20} "
                f"{image_tag:<15} {stage:<8} "
                f"{status_display} {tasks_str:<9}"
            )

        print()

    if provisioning_alerts:
        section_header("Provisioning warnings")
        for alert in provisioning_alerts:
            waiting = alert.demand - alert.occupied
            if alert.duration_seconds is None:
                detail = "underfilled, duration unknown"
            else:
                detail = f"provisioning stalled for {_format_elapsed(alert.duration_seconds)}"
            exhaustion = (
                " Batch reported zone resource pool exhaustion."
                if alert.resource_exhausted
                else ""
            )
            print(
                f"- {alert.job_name} ({alert.stage}): {alert.occupied}/{alert.demand} slots "
                f"occupied, {waiting} task(s) waiting; {detail}.{exhaustion}"
            )
        print()

    # Display recent workflows
    if recent_workflows:
        display_recent_workflows(recent_workflows)

    # Display recent batch jobs
    if recent_jobs:
        display_recent_batch_jobs(recent_jobs)

    # Summary
    total_active = len(workflows) + len(jobs)
    total_recent = len(recent_workflows or []) + len(recent_jobs or [])
    if total_active == 0 and total_recent == 0:
        print()  # Blank line before
        if supports_color():
            print("\033[90mAll pipelines idle\033[0m")
        else:
            print("All pipelines idle")
        print()  # Blank line after
    else:
        print()  # Blank line before
        parts = []
        if total_active > 0:
            parts.append(f"{len(workflows)} workflow(s), {len(jobs)} batch job(s) active")
        if total_recent > 0:
            parts.append(f"{len(recent_workflows or [])} workflow(s), {len(recent_jobs or [])} batch job(s) recent")
        print(f"Total: {'; '.join(parts)}")
        print()  # Blank line after


def _extract_workflow_exp_id(workflow: dict[str, Any]) -> str:
    """Extract exp_id from a workflow execution dict."""
    argument_str = workflow.get("argument", "{}")
    exp_id = "unknown"
    try:
        arg = json.loads(argument_str)
        exp_id = arg.get("exp_id", "unknown")
    except json.JSONDecodeError:
        pass
    if exp_id == "unknown":
        labels = workflow.get("labels", {})
        exp_id = labels.get("exp_id", "unknown")
    if len(exp_id) > 60:
        exp_id = exp_id[:57] + "..."
    return exp_id


def _format_elapsed(seconds: float) -> str:
    """Format a stall duration compactly for the warning block."""
    minutes = max(int(seconds // 60), 0)
    if minutes < 60:
        return f"{minutes}m"
    hours, remaining_minutes = divmod(minutes, 60)
    if remaining_minutes:
        return f"{hours}h {remaining_minutes}m"
    return f"{hours}h"


def display_recent_workflows(workflows: list[dict[str, Any]]) -> None:
    """Display recently completed workflows.

    Parameters
    ----------
    workflows : list[dict[str, Any]]
        List of recently completed workflow executions
    """
    print()  # Blank line before section
    section_header("Recently completed workflows")

    print("-" * 135)
    print(f"{'EXP_ID':<50} {'EXECUTION ID':<40} {'STATUS':<14} {'DURATION':<12} {'END TIME':<24}")
    print("-" * 135)

    for workflow in workflows:
        name = workflow.get("name", "")
        execution_id = name.split("/")[-1] if name else "unknown"

        exp_id = _extract_workflow_exp_id(workflow)
        if len(exp_id) > 50:
            exp_id = exp_id[:47] + "..."

        # Truncate execution_id if too long
        if len(execution_id) > 40:
            execution_id = execution_id[:37] + "..."

        # Status
        state = workflow.get("state", "UNKNOWN")
        status_padded = f"{state:<14}"
        status_display = format_status(status_padded, "workflow")

        # Duration
        start_time = workflow.get("startTime", "")
        end_time = workflow.get("endTime", "")
        duration_str = format_duration(start_time, end_time) if start_time and end_time else "unknown"

        # End time
        end_time_str = format_timestamp_local(end_time) if end_time else "unknown"

        print(f"{exp_id:<50} {execution_id:<40} {status_display} {duration_str:<12} {end_time_str:<24}")

    print()


def display_recent_batch_jobs(jobs: list[dict[str, Any]]) -> None:
    """Display recently completed batch jobs.

    Parameters
    ----------
    jobs : list[dict[str, Any]]
        List of recently completed batch jobs
    """
    section_header("Recently completed batch jobs")

    print("-" * 149)
    print(
        f"{'EXP_ID':<50} {'JOB NAME':<25} {'REGION':<13} {'STAGE':<8} "
        f"{'STATUS':<14} {'DURATION':<12} {'TASKS':<7}"
    )
    print("-" * 149)

    for job in jobs:
        job_name = job.get("name", "").split("/")[-1]
        if len(job_name) > 25:
            job_name = job_name[:22] + "..."

        status = job.get("status", {})
        state = status.get("state", "UNKNOWN")

        labels = job.get("labels", {})
        stage = labels.get("stage", "unknown")
        batch_region = get_job_region(job)

        # Get exp_id from task spec or labels
        task_groups_list = job.get("taskGroups", [])
        exp_id = "unknown"
        if task_groups_list:
            task_spec = task_groups_list[0].get("taskSpec", {})
            env_vars = task_spec.get("environment", {}).get("variables", {})
            exp_id = env_vars.get("EXP_ID", labels.get("exp_id", "unknown"))
        else:
            exp_id = labels.get("exp_id", "unknown")

        if len(exp_id) > 50:
            exp_id = exp_id[:47] + "..."

        # Duration from createTime to last status event or updateTime
        create_time = job.get("createTime", "")
        # Try to get end time from status events
        status_events = status.get("statusEvents", [])
        end_time = status_events[-1].get("eventTime", "") if status_events else ""
        if not end_time:
            end_time = job.get("updateTime", "")
        duration_str = format_duration(create_time, end_time) if create_time and end_time else "unknown"

        task_counts = extract_task_counts(job)
        succeeded = task_counts["SUCCEEDED"]
        failed = task_counts["FAILED"]
        completed = succeeded + failed
        total = extract_task_count(job) or completed
        tasks_str = f"{completed}/{total}" if total > 0 else "N/A"

        status_padded = f"{state:<14}"
        status_display = format_status(status_padded, "batch")

        print(
            f"{exp_id:<50} {job_name:<25} {batch_region:<13} {stage:<8} "
            f"{status_display} {duration_str:<12} {tasks_str:<7}"
        )

    print()
