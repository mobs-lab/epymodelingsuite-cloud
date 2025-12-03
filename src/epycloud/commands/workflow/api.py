"""API client functions for Cloud Workflows."""

import json
from typing import Any

import requests


def list_executions(
    project_id: str,
    region: str,
    workflow_name: str,
    token: str,
    limit: int | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """List workflow executions.

    Parameters
    ----------
    project_id : str
        GCP project ID
    region : str
        GCP region
    workflow_name : str
        Workflow name
    token : str
        OAuth access token
    limit : int | None
        Max number of executions to return
    status : str | None
        Filter by status (ACTIVE, SUCCEEDED, FAILED, CANCELLED)

    Returns
    -------
    list[dict[str, Any]]
        List of execution objects

    Raises
    ------
    requests.HTTPError
        If API request fails
    """
    # Build API URL
    list_url = (
        f"https://workflowexecutions.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/workflows/{workflow_name}/executions"
    )

    # Add query parameters
    params = []
    if limit:
        params.append(f"pageSize={limit}")
    if status:
        # Note: API filter syntax requires quotes: state="SUCCEEDED" or state="FAILED"
        params.append(f'filter=state="{status}"')

    if params:
        list_url += "?" + "&".join(params)

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
    return result.get("executions", [])


def get_execution(
    execution_name: str,
    token: str,
) -> dict[str, Any]:
    """Get execution details.

    Parameters
    ----------
    execution_name : str
        Full execution name (projects/.../locations/.../workflows/.../executions/...)
    token : str
        OAuth access token

    Returns
    -------
    dict[str, Any]
        Execution object

    Raises
    ------
    requests.HTTPError
        If API request fails
    """
    describe_url = f"https://workflowexecutions.googleapis.com/v1/{execution_name}"

    response = requests.get(
        describe_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    return response.json()


def cancel_execution(
    execution_name: str,
    token: str,
) -> dict[str, Any]:
    """Cancel a workflow execution.

    Parameters
    ----------
    execution_name : str
        Full execution name
    token : str
        OAuth access token

    Returns
    -------
    dict[str, Any]
        Response from cancel API

    Raises
    ------
    requests.HTTPError
        If API request fails
    """
    cancel_url = f"https://workflowexecutions.googleapis.com/v1/{execution_name}:cancel"

    response = requests.post(
        cancel_url,
        json={},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    return response.json()


def submit_execution(
    project_id: str,
    region: str,
    workflow_name: str,
    token: str,
    argument: dict[str, Any],
) -> dict[str, Any]:
    """Submit a new workflow execution.

    Parameters
    ----------
    project_id : str
        GCP project ID
    region : str
        GCP region
    workflow_name : str
        Workflow name
    token : str
        OAuth access token
    argument : dict[str, Any]
        Workflow arguments

    Returns
    -------
    dict[str, Any]
        Execution object

    Raises
    ------
    requests.HTTPError
        If API request fails
    """
    submit_url = (
        f"https://workflowexecutions.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/workflows/{workflow_name}/executions"
    )

    request_body = {"argument": json.dumps(argument)}

    response = requests.post(
        submit_url,
        json=request_body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    return response.json()


def enrich_executions_with_arguments(
    executions: list[dict[str, Any]],
    token: str,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Enrich executions with argument data from describe endpoint.

    The list endpoint doesn't include arguments, so we need to fetch them
    individually for each execution.

    Parameters
    ----------
    executions : list[dict[str, Any]]
        List of execution objects from list endpoint
    token : str
        OAuth access token
    verbose : bool
        Enable verbose output

    Returns
    -------
    list[dict[str, Any]]
        List of executions enriched with argument field
    """
    from epycloud.lib.output import warning

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


def parse_execution_name(
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
