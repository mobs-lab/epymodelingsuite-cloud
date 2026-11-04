"""Fetch workflow executions and Batch jobs for status."""

import json
import subprocess
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import requests

from epycloud.lib.command_helpers import DEFAULT_WORKFLOW_NAME, get_gcloud_access_token
from epycloud.lib.output import warning


def fetch_active_workflows(
    project_id: str,
    region: str,
    exp_id: str | None,
    verbose: bool,
    workflow_name: str = DEFAULT_WORKFLOW_NAME,
    token_provider=None,
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
    workflow_name : str
        Cloud Workflows workflow to query

    Returns
    -------
    list[dict[str, Any]]
        List of active workflow executions
    """
    base_url = (
        f"https://workflowexecutions.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/workflows/{workflow_name}/executions"
    )

    try:
        # Get auth token
        token = token_provider() if token_provider else get_gcloud_access_token(verbose)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Fetch all pages of results
        all_executions: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            # Build query params (requests handles URL encoding)
            params: dict[str, Any] = {
                "pageSize": 100,
                "filter": 'state="ACTIVE"',
                "view": "FULL",
            }
            if page_token:
                params["pageToken"] = page_token

            response = requests.get(base_url, params=params, headers=headers, timeout=30)
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


def fetch_recent_workflows(
    project_id: str,
    region: str,
    exp_id: str | None,
    since: datetime,
    verbose: bool,
    workflow_name: str = DEFAULT_WORKFLOW_NAME,
    token_provider=None,
) -> list[dict[str, Any]]:
    """Fetch recently completed workflow executions.

    Parameters
    ----------
    project_id : str
        GCP project ID
    region : str
        GCP region
    exp_id : str | None
        Optional experiment ID filter
    since : datetime
        Cutoff time, only include executions that ended after this time
    verbose : bool
        Verbose output
    workflow_name : str
        Cloud Workflows workflow to query

    Returns
    -------
    list[dict[str, Any]]
        List of recently completed workflow executions
    """
    base_url = (
        f"https://workflowexecutions.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/workflows/{workflow_name}/executions"
    )

    try:
        token = token_provider() if token_provider else get_gcloud_access_token(verbose)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        all_executions: list[dict[str, Any]] = []

        since_iso = since.astimezone(UTC).isoformat()
        params: dict[str, Any] = {
            "pageSize": 100,
            "filter": (
                '(state="SUCCEEDED" OR state="FAILED" OR state="CANCELLED") '
                f'AND endTime>="{since_iso}"'
            ),
            "view": "FULL",
            "orderBy": "endTime desc",
        }
        while True:
            response = requests.get(base_url, params=params.copy(), headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            all_executions.extend(result.get("executions", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break
            params["pageToken"] = page_token

        filtered = [
            execution for execution in all_executions
            if execution.get("endTime")
            and datetime.fromisoformat(execution["endTime"].replace("Z", "+00:00")) >= since
        ]

        # Filter by exp_id if provided
        if exp_id:
            filtered = [e for e in filtered if exp_id in e.get("argument", "")]

        # Sort by endTime descending
        filtered.sort(
            key=lambda e: datetime.fromisoformat(e["endTime"].replace("Z", "+00:00")),
            reverse=True,
        )

        return filtered

    except Exception as e:
        if verbose:
            warning(f"Failed to fetch recent workflows: {e}")
        return []


def fetch_active_batch_jobs(
    project_id: str,
    region: str | Sequence[str],
    exp_id: str | None,
    verbose: bool,
) -> list[dict[str, Any]]:
    """Fetch active Cloud Batch jobs.

    Parameters
    ----------
    project_id : str
        GCP project ID
    region : str | Sequence[str]
        One or more Cloud Batch regions
    exp_id : str | None
        Optional experiment ID filter
    verbose : bool
        Verbose output

    Returns
    -------
    list[dict[str, Any]]
        List of active batch jobs
    """
    state_filter = "(status.state:RUNNING OR status.state:QUEUED OR status.state:SCHEDULED)"
    if exp_id:
        from epycloud.lib.validation import sanitize_label_value

        exp_id_label = sanitize_label_value(exp_id)
        filter_expr = f"{state_filter} AND labels.exp_id={exp_id_label}"
    else:
        filter_expr = state_filter

    regions = (region,) if isinstance(region, str) else tuple(region)
    all_jobs: list[dict[str, Any]] = []
    if len(regions) > 1:
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            results = pool.map(
                lambda r: fetch_active_batch_jobs(project_id, r, exp_id, verbose), regions
            )
            all_jobs = [job for jobs in results for job in jobs]
        regions = ()
    for batch_region in regions:
        cmd = [
            "gcloud",
            "batch",
            "jobs",
            "list",
            f"--project={project_id}",
            f"--location={batch_region}",
            "--format=json",
            f"--filter={filter_expr}",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            if not result.stdout.strip():
                continue
            jobs = json.loads(result.stdout)
            for job in jobs:
                job["region"] = batch_region
            all_jobs.extend(jobs)
        except Exception as e:
            if verbose:
                warning(f"Failed to fetch batch jobs in {batch_region}: {e}")

    # Sort by experiment and region for stable output across calls.
    def get_job_exp_id(job: dict[str, Any]) -> tuple[str, str]:
        task_groups = job.get("taskGroups", [])
        if task_groups:
            task_spec = task_groups[0].get("taskSpec", {})
            env_vars = task_spec.get("environment", {}).get("variables", {})
            exp_id = env_vars.get("EXP_ID", job.get("labels", {}).get("exp_id", ""))
        else:
            exp_id = job.get("labels", {}).get("exp_id", "")
        return exp_id, job.get("region", "")

    all_jobs.sort(key=get_job_exp_id)
    return all_jobs


def fetch_recent_batch_jobs(
    project_id: str,
    region: str | Sequence[str],
    exp_id: str | None,
    since: datetime,
    verbose: bool,
) -> list[dict[str, Any]]:
    """Fetch recently completed Cloud Batch jobs.

    Parameters
    ----------
    project_id : str
        GCP project ID
    region : str | Sequence[str]
        One or more Cloud Batch regions
    exp_id : str | None
        Optional experiment ID filter
    since : datetime
        Cutoff time, only include jobs that ended after this time
    verbose : bool
        Verbose output

    Returns
    -------
    list[dict[str, Any]]
        List of recently completed batch jobs
    """
    state_filter = "(status.state:SUCCEEDED OR status.state:FAILED OR status.state:CANCELLED)"
    if exp_id:
        from epycloud.lib.validation import sanitize_label_value

        exp_id_label = sanitize_label_value(exp_id)
        filter_expr = f"{state_filter} AND labels.exp_id={exp_id_label}"
    else:
        filter_expr = state_filter

    regions = (region,) if isinstance(region, str) else tuple(region)
    since_iso = since.astimezone(UTC).isoformat()
    filter_expr += f' AND updateTime>="{since_iso}"'
    filtered: list[dict[str, Any]] = []
    if len(regions) > 1:
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            results = pool.map(
                lambda r: fetch_recent_batch_jobs(project_id, r, exp_id, since, verbose), regions
            )
            filtered = [job for jobs in results for job in jobs]
        regions = ()
    for batch_region in regions:
        cmd = [
            "gcloud",
            "batch",
            "jobs",
            "list",
            f"--project={project_id}",
            f"--location={batch_region}",
            "--format=json",
            f"--filter={filter_expr}",
            "--sort-by=~createTime",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            if not result.stdout.strip():
                continue
            for job in json.loads(result.stdout):
                status_events = job.get("status", {}).get("statusEvents", [])
                update_time = (
                    status_events[-1].get("eventTime", "")
                    if status_events
                    else job.get("updateTime", "")
                )
                if not update_time:
                    update_time = job.get("createTime", "")
                if update_time and datetime.fromisoformat(update_time.replace("Z", "+00:00")) >= since:
                    job["region"] = batch_region
                    filtered.append(job)
        except Exception as e:
            if verbose:
                warning(f"Failed to fetch recent batch jobs in {batch_region}: {e}")

    filtered.sort(key=lambda job: job.get("createTime", ""), reverse=True)
    return filtered
