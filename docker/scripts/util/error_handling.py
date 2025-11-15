"""
Standardized error handling for pipeline stages.
"""

import logging
import sys
from typing import NoReturn


def handle_stage_error(
    stage_name: str,
    error: Exception,
    logger: logging.Logger,
) -> NoReturn:
    """
    Standard error handler for pipeline stages.

    Logs error with full traceback and exits with code 1.

    Parameters
    ----------
    stage_name : str
        Stage identifier (e.g., "Stage A (Builder)", "Task 42")
    error : Exception
        The exception that was caught
    logger : logging.Logger
        Logger instance for the stage

    Examples
    --------
    >>> from util.logger import setup_logger
    >>> from util.error_handling import handle_stage_error
    >>>
    >>> logger = setup_logger("builder")
    >>> try:
    ...     # ... stage logic ...
    ...     pass
    ... except Exception as e:
    ...     handle_stage_error("Stage A (Builder)", e, logger)
    """
    logger.error(
        f"{stage_name} failed: {type(error).__name__}: {error}",
        exc_info=True,  # Includes full traceback
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "failed_stage": stage_name,
        },
    )
    sys.exit(1)
