"""Handler functions for workflow subcommands."""

import json
import sys
from datetime import UTC, datetime
from typing import Any

import requests

from epycloud.exceptions import ConfigError
from epycloud.execution import ExecutionAuthenticationError, RunQuery, get_execution_backend
from epycloud.lib.command_helpers import (
    get_gcloud_access_token,
    get_workflow_name,
    require_config,
)
from epycloud.lib.formatters import parse_since_time
from epycloud.lib.output import error, info, status, success, warning

from . import api, display, streaming


def _get_backend(config: dict[str, Any], verbose: bool):
    """Create the configured backend while preserving patchable legacy boundaries."""

    return get_execution_backend(
        config,
        verbose=verbose,
        token_provider=lambda: get_gcloud_access_token(verbose),
        workflow_api=api,
    )


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

    try:
        _get_backend(ctx["config"], ctx["verbose"])
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

    # Make API request
    try:
        cutoff_time = parse_since_time(args.since) if args.since else None
        backend = _get_backend(config, verbose)
        records = backend.list_runs(
            RunQuery(
                limit=args.limit,
                status=args.status,
                since=cutoff_time,
                experiment_id=args.exp_id,
            )
        )
        if not records:
            status("No workflow executions found")
            return 0

        # Display executions
        executions = [record.raw for record in records]
        display.display_execution_list(executions, region)
        return 0

    except ExecutionAuthenticationError as e:
        error(f"Failed to get access token: {e}")
        return 1
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
    if not project_id:
        error("google_cloud.project_id not configured")
        return 2

    # Make API request
    try:
        backend = _get_backend(config, verbose)
        record = backend.describe_run(args.execution_id)
        display.display_execution_details(record.raw)
        return 0

    except ExecutionAuthenticationError as e:
        error(f"Failed to get access token: {e}")
        return 1
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

    status(f"Fetching logs for execution: {execution_id}")

    workflow_name = get_workflow_name(config)

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
        status("Note: Workflow logs may not be available immediately after submission")
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

    if not project_id:
        error("google_cloud.project_id not configured")
        return 2

    backend = _get_backend(config, verbose)
    run_ref = backend.resolve_run_ref(args.execution_id)

    status(f"Cancelling execution: {args.execution_id}")

    if dry_run:
        status(f"Would cancel: {run_ref.resource_name}")
        return 0

    # Make API request
    try:
        result = backend.cancel_run(args.execution_id, include_jobs=not args.only_workflow)
        success(f"Execution cancelled: {args.execution_id}")

        cancelled_count = 0
        failed_count = 0
        for child in result.children:
            if child.outcome == "cancelled":
                status(f"Cancelled job: {child.job_id}")
                cancelled_count += 1
            elif child.outcome == "not_found":
                if verbose:
                    status(f"Job not found: {child.job_id}")
            elif child.outcome == "already_complete":
                status(f"Job already completed: {child.job_id}")
            else:
                if child.status_code is not None:
                    warning(f"Failed to cancel job {child.job_id}: HTTP {child.status_code}")
                else:
                    warning(f"Failed to cancel job {child.job_id}: {child.message}")
                failed_count += 1

        if cancelled_count > 0:
            success(f"Cancelled {cancelled_count} batch job(s)")
        if failed_count > 0:
            warning(f"Failed to cancel {failed_count} batch job(s)")
            return 1

        return 0

    except ExecutionAuthenticationError as e:
        error(f"Failed to get access token: {e}")
        return 1
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

    if not project_id:
        error("google_cloud.project_id not configured")
        return 2

    status(f"Fetching execution details: {args.execution_id}")

    try:
        backend = _get_backend(config, verbose)
        plan = backend.plan_retry(args.execution_id)
        original_arg = plan.metadata["arguments"]

        status("Retrying execution with same parameters:")
        print(json.dumps(original_arg, indent=2))

        if dry_run:
            status("Would resubmit workflow with above parameters")
            return 0

        run_ref = backend.submit_pipeline(plan)
        new_execution_id = run_ref.run_id

        success(f"New execution submitted: {new_execution_id}")
        info(f"Monitor with: epycloud workflow describe {new_execution_id}")
        return 0

    except ExecutionAuthenticationError as e:
        error(f"Failed to get access token: {e}")
        return 1
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
