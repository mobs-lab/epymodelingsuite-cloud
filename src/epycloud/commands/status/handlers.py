"""Status command handlers."""

import time
from datetime import datetime
from typing import Any

from epycloud.commands.status.operations import (
    display_status,
    fetch_active_batch_jobs,
    fetch_active_workflows,
)
from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import get_google_cloud_config, require_config
from epycloud.lib.formatters import format_timestamp_local
from epycloud.lib.output import error, info, warning


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
        workflows = fetch_active_workflows(
            project_id=project_id,
            region=region,
            exp_id=exp_id,
            verbose=verbose,
        )

        # Fetch active batch jobs
        jobs = fetch_active_batch_jobs(
            project_id=project_id,
            region=region,
            exp_id=exp_id,
            verbose=verbose,
        )

        # Display status
        display_status(workflows, jobs, exp_id)

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
                workflows = fetch_active_workflows(
                    project_id=project_id,
                    region=region,
                    exp_id=exp_id,
                    verbose=verbose,
                )

                jobs = fetch_active_batch_jobs(
                    project_id=project_id,
                    region=region,
                    exp_id=exp_id,
                    verbose=verbose,
                )

                display_status(workflows, jobs, exp_id)

                # Show refresh time
                now = format_timestamp_local(datetime.now().isoformat())
                print(f"Last updated: {now} (refreshing every {interval}s)")

            except Exception as e:
                warning(f"Failed to refresh: {e}")

            # Wait before next refresh
            time.sleep(interval)

    except KeyboardInterrupt:
        print()
        info("Stopped watching")
        return 0
