"""Log streaming functionality."""

import json
import subprocess
import sys
import time

from epycloud.lib.output import error, info

from .display import display_streaming_log_entry


def stream_logs(
    project_id: str,
    log_filter: str,
    verbose: bool,
) -> int:
    """Stream logs in follow mode.

    Parameters
    ----------
    project_id : str
        GCP project ID
    log_filter : str
        Cloud Logging filter
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
            # Add timestamp filter for new logs
            current_filter = log_filter
            if last_timestamp:
                current_filter += f' AND timestamp>"{last_timestamp}"'

            # Fetch logs
            cmd = [
                "gcloud",
                "logging",
                "read",
                current_filter,
                f"--project={project_id}",
                "--limit=100",
                "--format=json",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                logs = json.loads(result.stdout)

                # Display new logs (in chronological order)
                for entry in reversed(logs):
                    timestamp = display_streaming_log_entry(entry)
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
