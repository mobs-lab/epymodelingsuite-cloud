"""Status command handlers."""

import time
from datetime import datetime
from typing import Any

from epycloud.commands.status.operations import (
    display_status,
    fetch_active_batch_jobs,
    fetch_active_workflows,
    fetch_recent_batch_jobs,
    fetch_recent_workflows,
)
from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import get_google_cloud_config, require_config
from epycloud.lib.formatters import format_timestamp_local, parse_since_time
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

    # Parse --recent time window
    recent_window = args.recent  # None, "1h", "30m", etc.
    if recent_window is not None:
        since = parse_since_time(recent_window)
        if since is None:
            error(f"Invalid time format for --recent: '{recent_window}' (try 30m, 1h, 2d)")
            return 2
    else:
        since = None

    # Watch mode
    if args.watch:
        return _watch_status(
            project_id=project_id,
            region=region,
            exp_id=args.exp_id,
            interval=args.interval,
            verbose=verbose,
            recent=recent_window,
        )

    # One-time status check
    return _show_status(
        project_id=project_id,
        region=region,
        exp_id=args.exp_id,
        verbose=verbose,
        since=since,
    )


def _show_status(
    project_id: str,
    region: str,
    exp_id: str | None,
    verbose: bool,
    since: datetime | None = None,
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
    since : datetime | None
        If set, also show recently completed items since this time

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

        # Fetch recent items if requested
        recent_workflows = None
        recent_jobs = None
        if since is not None:
            recent_workflows = fetch_recent_workflows(
                project_id=project_id,
                region=region,
                exp_id=exp_id,
                since=since,
                verbose=verbose,
            )
            recent_jobs = fetch_recent_batch_jobs(
                project_id=project_id,
                region=region,
                exp_id=exp_id,
                since=since,
                verbose=verbose,
            )

        # Display status
        display_status(workflows, jobs, exp_id, recent_workflows, recent_jobs)

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
    recent: str | None = None,
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
    recent : str | None
        Recent time window string (e.g., "1h", "30m") — re-parsed each refresh

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

                # Fetch recent items if requested (re-parse each refresh)
                recent_workflows = None
                recent_jobs = None
                if recent is not None:
                    since = parse_since_time(recent)
                    if since is not None:
                        recent_workflows = fetch_recent_workflows(
                            project_id=project_id,
                            region=region,
                            exp_id=exp_id,
                            since=since,
                            verbose=verbose,
                        )
                        recent_jobs = fetch_recent_batch_jobs(
                            project_id=project_id,
                            region=region,
                            exp_id=exp_id,
                            since=since,
                            verbose=verbose,
                        )

                display_status(workflows, jobs, exp_id, recent_workflows, recent_jobs)

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
