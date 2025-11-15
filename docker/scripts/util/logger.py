"""
Dual-mode structured logging for pipeline stages.

Provides human-readable console logs for local development and
JSON structured logs for Google Cloud Logging integration.
"""

import logging
import os
import sys
from typing import Optional


def setup_logger(
    name: str,
    task_index: Optional[int] = None,
    exp_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> logging.Logger:
    """
    Setup dual-mode logger for pipeline stages.

    Mode is determined by EXECUTION_MODE environment variable:
    - local: Human-readable console logging with timestamps
    - cloud: JSON structured logging for Google Cloud Logging

    Parameters
    ----------
    name : str
        Logger name (e.g., "builder", "runner", "output")
    task_index : int, optional
        Task index for runner stage (added to context)
    exp_id : str, optional
        Experiment ID (added to all log entries as metadata)
    run_id : str, optional
        Run ID (added to all log entries as metadata)

    Returns
    -------
    logging.Logger
        Configured logger instance

    Examples
    --------
    >>> # In main_builder.py
    >>> logger = setup_logger("builder", exp_id="flu-round05", run_id="20251103-143052")
    >>> logger.info("Starting Stage A")

    >>> # In main_runner.py
    >>> logger = setup_logger("runner", task_index=42, exp_id="flu-round05", run_id="20251103-143052")
    >>> logger.info("Processing task", extra={"workload_type": "simulation"})

    Environment Variables
    ---------------------
    EXECUTION_MODE : str
        Execution mode: "local" (console) or "cloud" (JSON)
    LOG_LEVEL : str
        Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
    """
    logger = logging.getLogger(name)

    # Set log level from environment (default: INFO)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers to avoid duplicates if called multiple times
    logger.handlers.clear()

    # Get execution mode
    execution_mode = os.getenv("EXECUTION_MODE", "cloud").lower()

    # Create handler (both modes write to stdout for Cloud Logging compatibility)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)

    if execution_mode == "cloud":
        # Cloud mode: JSON structured logging
        formatter = _create_cloud_formatter(name, task_index, exp_id, run_id)
    else:
        # Local mode: Human-readable console logging
        formatter = _create_local_formatter(name, task_index)

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Don't propagate to root logger (prevents duplicate logs)
    logger.propagate = False

    return logger


def _create_cloud_formatter(
    stage: str,
    task_index: Optional[int],
    exp_id: Optional[str],
    run_id: Optional[str],
) -> logging.Formatter:
    """
    Create JSON formatter for Google Cloud Logging.

    Uses python-json-logger to output structured JSON logs that
    Google Cloud Logging can automatically parse and index.
    """
    try:
        from pythonjsonlogger import jsonlogger
    except ImportError:
        raise ImportError(
            "python-json-logger is required for cloud mode. "
            "Add 'python-json-logger>=2.0.0' to docker/requirements.txt"
        )

    # Custom formatter that adds context fields to every log entry
    class CloudFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            """Add custom fields to every log entry."""
            super().add_fields(log_record, record, message_dict)

            # Add stage context (always present)
            log_record["stage"] = stage

            # Add optional context
            if exp_id:
                log_record["exp_id"] = exp_id
            if run_id:
                log_record["run_id"] = run_id
            if task_index is not None:
                log_record["task_index"] = task_index

            # Rename 'levelname' to 'severity' for Cloud Logging compatibility
            if "levelname" in log_record:
                log_record["severity"] = log_record.pop("levelname")

    # Format string defines which built-in fields to include
    # timestamp, name, severity, and message are essential
    # extra fields from logger.info(..., extra={}) are automatically included
    return CloudFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S.%fZ",  # ISO 8601 format
    )


def _create_local_formatter(
    stage: str,
    task_index: Optional[int],
) -> logging.Formatter:
    """
    Create human-readable formatter for local development.

    Outputs clean console logs with timestamps, stage name, and severity.
    Optionally includes task index for runner stage.
    """
    # Build format string based on context
    format_parts = [
        "%(asctime)s",  # Timestamp
        stage,  # Stage name (static, cleaner than %(name)s)
        "%(levelname)s",  # Severity
    ]

    if task_index is not None:
        format_parts.append(f"[Task {task_index}]")

    format_parts.append("%(message)s")

    format_string = " ".join(format_parts)

    return logging.Formatter(
        fmt=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",  # Human-readable timestamp
    )


class StorageLogger:
    """
    Wrapper for storage operation logging with verbosity control.

    Reduces log noise by only logging storage operations when
    STORAGE_VERBOSE=true is set. This prevents thousands of
    log lines from I/O operations in large pipelines.

    Examples
    --------
    >>> logger = setup_logger("storage")
    >>> storage_logger = StorageLogger(logger)
    >>>
    >>> # Only logs if STORAGE_VERBOSE=true
    >>> storage_logger.log_read("gs://bucket/file.pkl", 1024)
    >>> storage_logger.log_write("/data/bucket/output.csv", 2048)
    >>>
    >>> # Always logs (operations, not verbose I/O)
    >>> storage_logger.log_operation("Upload", "gs://bucket/result.pkl")
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize storage logger.

        Parameters
        ----------
        logger : logging.Logger
            Parent logger to use for output
        """
        self.logger = logger
        self.verbose = os.getenv("STORAGE_VERBOSE", "false").lower() == "true"

    def log_read(self, path: str, size: int) -> None:
        """
        Log storage read operation (verbose mode only).

        Parameters
        ----------
        path : str
            File path that was read
        size : int
            Number of bytes read
        """
        if self.verbose:
            self.logger.debug(f"Read {size:,} bytes from {path}")

    def log_write(self, path: str, size: int) -> None:
        """
        Log storage write operation (verbose mode only).

        Parameters
        ----------
        path : str
            File path that was written
        size : int
            Number of bytes written
        """
        if self.verbose:
            self.logger.debug(f"Wrote {size:,} bytes to {path}")

    def log_operation(self, operation: str, path: str) -> None:
        """
        Log important storage operation (always logged).

        Use for operations like uploads, downloads, deletes that
        should always be visible regardless of verbosity setting.

        Parameters
        ----------
        operation : str
            Operation type (e.g., "Upload", "Download", "Delete")
        path : str
            File path involved
        """
        self.logger.info(f"{operation}: {path}")
