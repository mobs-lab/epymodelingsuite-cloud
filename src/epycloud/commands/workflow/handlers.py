"""Handler functions for workflow subcommands."""

import json
import sys
from datetime import UTC, datetime
from typing import Any

import requests

from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import (
    get_gcloud_access_token,
    require_config,
)
from epycloud.lib.formatters import parse_since_time
from epycloud.lib.output import error, info, success, warning

from . import api, display, streaming


def handle(ctx: dict[str, Any]) -> int:
    """Handle workflow command.

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

    # Validate configuration
    try:
        require_config(ctx)
    except ConfigError as e:
        error(str(e))
        return 2

    if not args.workflow_subcommand:
        # Print help instead of error message
        if hasattr(args, "_workflow_parser"):
            args._workflow_parser.print_help()
        else:
            error("No subcommand specified. Use 'epycloud workflow --help'")
        return 1

    # Route to subcommand handler
    if args.workflow_subcommand == "list":
        return handle_list(ctx)
    elif args.workflow_subcommand == "describe":
        return handle_describe(ctx)
    elif args.workflow_subcommand == "logs":
        return handle_logs(ctx)
    elif args.workflow_subcommand == "cancel":
        return handle_cancel(ctx)
    elif args.workflow_subcommand == "retry":
        return handle_retry(ctx)
    else:
        error(f"Unknown subcommand: {args.workflow_subcommand}")
        return 1


def handle_list(ctx: dict[str, Any]) -> int:
    """Handle workflow list command.

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

    # Get auth token
    try:
        token = get_gcloud_access_token(verbose)
    except Exception as e:
        error(f"Failed to get access token: {e}")
        return 1

    # Make API request
    try:
        executions = api.list_executions(
            project_id, region, workflow_name, token, args.limit, args.status
        )

        # Apply time-based filter first (doesn't need arguments)
        if args.since:
            cutoff_time = parse_since_time(args.since)
            if cutoff_time:
                executions = [
                    e for e in executions if _parse_timestamp(e.get("startTime", "")) > cutoff_time
                ]

        if not executions:
            info("No workflow executions found")
            return 0

        # Enrich executions with arguments (list endpoint doesn't include them)
        executions = api.enrich_executions_with_arguments(executions, token, verbose)

        # Apply exp_id filter after enrichment (needs arguments)
        if args.exp_id:
            executions = [
                e
                for e in executions
                if args.exp_id in e.get("argument", e.get("workflowRevisionId", ""))
            ]

        if not executions:
            info("No workflow executions found")
            return 0

        # Display executions
        display.display_execution_list(executions, region)
        return 0

    except requests.HTTPError as e:
        error(f"Failed to list executions: HTTP {e.response.status_code}")
        if verbose and e.response is not None:
            print(e.response.text, file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Failed to list executions: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def handle_describe(ctx: dict[str, Any]) -> int:
    """Handle workflow describe command.

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
    execution_name = api.parse_execution_name(
        args.execution_id, project_id, region, "epymodelingsuite-pipeline"
    )

    # Get auth token
    try:
        token = get_gcloud_access_token(verbose)
    except Exception as e:
        error(f"Failed to get access token: {e}")
        return 1

    # Make API request
    try:
        execution = api.get_execution(execution_name, token)
        display.display_execution_details(execution)
        return 0

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            error(f"Execution not found: {args.execution_id}")
        else:
            status_code = e.response.status_code if e.response else "unknown"
            error(f"Failed to describe execution: HTTP {status_code}")
        if verbose and e.response is not None:
            print(e.response.text, file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Failed to describe execution: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def handle_logs(ctx: dict[str, Any]) -> int:
    """Handle workflow logs command.

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

    workflow_name = "epymodelingsuite-pipeline"

    if args.follow:
        # For follow mode, we need to continuously poll
        return streaming.stream_logs(project_id, execution_id, region, workflow_name, verbose)

    # One-time log fetch
    logs, exit_code = streaming.fetch_logs(
        project_id, execution_id, region, workflow_name, args.tail, verbose
    )

    if exit_code != 0:
        return exit_code

    if not logs:
        warning("No logs found for this execution")
        info("Note: Workflow logs may not be available immediately after submission")
        return 0

    # Display logs
    display.display_logs(logs)
    return 0


def handle_cancel(ctx: dict[str, Any]) -> int:
    """Handle workflow cancel command.

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
    execution_name = api.parse_execution_name(
        args.execution_id, project_id, region, "epymodelingsuite-pipeline"
    )

    info(f"Cancelling execution: {args.execution_id}")

    if dry_run:
        info(f"Would cancel: {execution_name}")
        return 0

    # Get auth token
    try:
        token = get_gcloud_access_token(verbose)
    except Exception as e:
        error(f"Failed to get access token: {e}")
        return 1

    # Make API request
    try:
        api.cancel_execution(execution_name, token)
        success(f"Execution cancelled: {args.execution_id}")
        return 0

    except requests.HTTPError as e:
        if e.response is not None:
            if e.response.status_code == 404:
                error(f"Execution not found: {args.execution_id}")
            elif e.response.status_code == 400:
                warning("Execution may already be completed or cancelled")
            else:
                error(f"Failed to cancel execution: HTTP {e.response.status_code}")
            if verbose:
                print(e.response.text, file=sys.stderr)
        else:
            error("Failed to cancel execution: No response")
        return 1
    except Exception as e:
        error(f"Failed to cancel execution: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def handle_retry(ctx: dict[str, Any]) -> int:
    """Handle workflow retry command.

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
    execution_name = api.parse_execution_name(
        args.execution_id, project_id, region, "epymodelingsuite-pipeline"
    )

    info(f"Fetching execution details: {args.execution_id}")

    try:
        token = get_gcloud_access_token(verbose)
    except Exception as e:
        error(f"Failed to get access token: {e}")
        return 1

    try:
        # Get original execution details
        execution = api.get_execution(execution_name, token)

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
        result = api.submit_execution(
            project_id, region, "epymodelingsuite-pipeline", token, original_arg
        )
        new_execution_name = result.get("name", "")
        new_execution_id = new_execution_name.split("/")[-1] if new_execution_name else ""

        success(f"New execution submitted: {new_execution_id}")
        info(f"Monitor with: epycloud workflow describe {new_execution_id}")
        return 0

    except requests.HTTPError as e:
        if e.response is not None:
            if e.response.status_code == 404:
                error(f"Execution not found: {args.execution_id}")
            else:
                error(f"Failed to retry execution: HTTP {e.response.status_code}")
            if verbose:
                print(e.response.text, file=sys.stderr)
        else:
            error("Failed to retry execution: No response")
        return 1
    except Exception as e:
        error(f"Failed to retry execution: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _parse_timestamp(timestamp: str) -> datetime:
    """Parse ISO 8601 timestamp.

    Parameters
    ----------
    timestamp : str
        ISO 8601 timestamp string

    Returns
    -------
    datetime
        Datetime object
    """
    try:
        # Handle different timestamp formats
        if timestamp.endswith("Z"):
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return datetime.fromisoformat(timestamp)
    except (ValueError, AttributeError):
        return datetime.min.replace(tzinfo=UTC)
