"""Log streaming functionality for workflow command."""

import json
import subprocess
import time

from epycloud.lib.output import error, info

from .display import display_log_stream


def stream_logs(
    project_id: str,
    execution_id: str,
    region: str,
    workflow_name: str,
    verbose: bool = False,
) -> int:
    """Stream logs in follow mode.

    Parameters
    ----------
    project_id : str
        GCP project ID
    execution_id : str
        Execution ID
    region : str
        GCP region
    workflow_name : str
        Workflow name
    verbose : bool
        Verbose output

    Returns
    -------
    int
        Exit code
    """
    info("Streaming logs (Ctrl+C to stop)...")
    print()

    last_timestamp = None
    poll_interval = 5  # seconds

    try:
        while True:
            # Build filter
            filter_parts = [
                'resource.type="workflows.googleapis.com/Workflow"',
                f'resource.labels.workflow_id="{workflow_name}"',
                f'resource.labels.location="{region}"',
                f'labels.execution_id="{execution_id}"',
            ]

            if last_timestamp:
                filter_parts.append(f'timestamp>"{last_timestamp}"')

            log_filter = " AND ".join(filter_parts)

            # Fetch logs
            cmd = [
                "gcloud",
                "logging",
                "read",
                log_filter,
                "--project",
                project_id,
                "--limit",
                "100",
                "--format",
                "json",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                logs = json.loads(result.stdout)

                # Display new logs
                for entry in reversed(logs):
                    timestamp = display_log_stream(entry)
                    # Update last timestamp
                    if timestamp:
                        last_timestamp = timestamp

            # Wait before next poll
            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print()
        info("Stopped streaming logs")
        return 0
    except Exception as e:
        error(f"Failed to stream logs: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def fetch_logs(
    project_id: str,
    execution_id: str,
    region: str,
    workflow_name: str,
    limit: int = 100,
    verbose: bool = False,
) -> tuple[list[dict], int]:
    """Fetch logs for an execution.

    Parameters
    ----------
    project_id : str
        GCP project ID
    execution_id : str
        Execution ID
    region : str
        GCP region
    workflow_name : str
        Workflow name
    limit : int
        Max number of log entries to fetch
    verbose : bool
        Verbose output

    Returns
    -------
    tuple[list[dict], int]
        (list of log entries, exit code)
    """
    # Build gcloud logging query
    # Logs from Cloud Workflows are in Cloud Logging
    filter_parts = [
        'resource.type="workflows.googleapis.com/Workflow"',
        f'resource.labels.workflow_id="{workflow_name}"',
        f'resource.labels.location="{region}"',
        f'labels.execution_id="{execution_id}"',
    ]

    log_filter = " AND ".join(filter_parts)

    # Build gcloud command
    cmd = [
        "gcloud",
        "logging",
        "read",
        log_filter,
        "--project",
        project_id,
        "--limit",
        str(limit),
        "--format",
        "json",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            return [], 0

        # Parse and return logs
        logs = json.loads(result.stdout)
        return logs, 0

    except subprocess.CalledProcessError as e:
        error("Failed to fetch logs")
        if verbose:
            print(e.stderr)
        return [], 1
    except Exception as e:
        error(f"Failed to fetch logs: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return [], 1
