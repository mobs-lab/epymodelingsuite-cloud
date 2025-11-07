"""
Command Helper Functions.

This module provides common helper functions used across epycloud commands to
reduce code duplication and ensure consistent behavior.

Functions
---------
require_config : Get configuration with validation
get_google_cloud_config : Get Google Cloud config section with validation
handle_dry_run : Handle dry-run mode with consistent messaging
get_project_root : Get project root directory path
get_gcloud_access_token : Retrieve Google Cloud access token
prepare_subprocess_env : Prepare environment variables for subprocess calls
"""

import os
import subprocess
from pathlib import Path
from typing import TypedDict

from epycloud.exceptions import CloudAPIError, ConfigError
from epycloud.lib.output import info


class CommandContext(TypedDict):
    """
    Type-safe command context dictionary.

    Attributes
    ----------
    config : dict
        Loaded configuration dictionary.
    environment : str
        Active environment name (dev, prod, local).
    profile : str or None
        Active profile name (flu, covid, rsv, etc.).
    verbose : bool
        Enable verbose output.
    quiet : bool
        Suppress informational output.
    dry_run : bool
        Simulate actions without executing them.
    args : argparse.Namespace
        Parsed command-line arguments.
    """

    config: dict
    environment: str
    profile: str | None
    verbose: bool
    quiet: bool
    dry_run: bool
    args: object  # argparse.Namespace


def require_config(ctx: CommandContext) -> dict:
    """
    Ensure configuration is loaded and return it.

    Parameters
    ----------
    ctx : CommandContext
        Command context dictionary.

    Returns
    -------
    dict
        Configuration dictionary.

    Raises
    ------
    ConfigError
        If configuration is not loaded or is empty.

    Examples
    --------
    >>> config = require_config(ctx)
    >>> project_id = config['google_cloud']['project_id']
    """
    config = ctx.get("config")
    if not config:
        raise ConfigError("Configuration not loaded. Run 'epycloud config init' first")
    return config


def get_google_cloud_config(ctx: CommandContext) -> dict:
    """
    Get Google Cloud configuration section with validation.

    Parameters
    ----------
    ctx : CommandContext
        Command context dictionary.

    Returns
    -------
    dict
        Google Cloud configuration section containing project_id, region, etc.

    Raises
    ------
    ConfigError
        If configuration is not loaded or required Google Cloud keys are missing.

    Examples
    --------
    >>> gcloud_config = get_google_cloud_config(ctx)
    >>> project_id = gcloud_config['project_id']
    >>> region = gcloud_config['region']
    """
    config = require_config(ctx)
    gcloud_config = config.get("google_cloud", {})

    # Validate required keys
    required_keys = ["project_id", "region", "bucket_name"]
    missing = [k for k in required_keys if not gcloud_config.get(k)]

    if missing:
        raise ConfigError(
            f"Missing required Google Cloud config: {', '.join(missing)}. "
            "Run 'epycloud config init' to set up configuration."
        )

    return gcloud_config


def handle_dry_run(ctx: CommandContext, message: str, details: dict = None) -> bool:
    """
    Handle dry-run mode with consistent messaging.

    Parameters
    ----------
    ctx : CommandContext
        Command context dictionary.
    message : str
        Main action description (e.g., "Submit workflow for exp-id: test").
    details : dict, optional
        Additional details to display (e.g., parameters, environment variables).

    Returns
    -------
    bool
        True if in dry-run mode (caller should return early), False otherwise.

    Examples
    --------
    >>> if handle_dry_run(ctx, "Submit workflow", {"exp_id": "test", "run_id": "123"}):
    ...     return 0
    >>> # Continue with actual execution
    """
    if not ctx.get("dry_run"):
        return False

    info(f"DRY RUN: {message}")

    if details:
        for key, value in details.items():
            info(f"  {key}: {value}")

    return True


def get_project_root() -> Path:
    """
    Get project root directory path.

    Returns
    -------
    Path
        Absolute path to project root directory.

    Notes
    -----
    Assumes this file is located at: project_root/src/epycloud/lib/command_helpers.py
    Navigates up 4 levels to reach project root.

    Examples
    --------
    >>> root = get_project_root()
    >>> terraform_dir = root / "terraform"
    >>> docker_dir = root / "docker"
    """
    return Path(__file__).parent.parent.parent.parent


def get_gcloud_access_token(verbose: bool = False) -> str:
    """
    Retrieve Google Cloud access token using gcloud CLI.

    Parameters
    ----------
    verbose : bool, optional
        Print detailed error messages on failure, by default False.

    Returns
    -------
    str
        Google Cloud access token.

    Raises
    ------
    CloudAPIError
        If gcloud CLI is not available or authentication fails.

    Examples
    --------
    >>> token = get_gcloud_access_token(verbose=True)
    >>> headers = {"Authorization": f"Bearer {token}"}
    """
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True,
        )
        access_token = result.stdout.strip()

        if not access_token:
            raise CloudAPIError(
                "gcloud returned empty access token. "
                "Ensure you are authenticated: gcloud auth login"
            )

        return access_token

    except FileNotFoundError:
        raise CloudAPIError(
            "gcloud CLI not found. "
            "Install it from: https://cloud.google.com/sdk/docs/install"
        )
    except subprocess.CalledProcessError as e:
        error_msg = "Failed to get Google Cloud access token"
        if verbose and e.stderr:
            error_msg += f": {e.stderr.strip()}"
        raise CloudAPIError(error_msg)


def prepare_subprocess_env(base_vars: dict = None) -> dict:
    """
    Prepare environment variables for subprocess calls.

    Parameters
    ----------
    base_vars : dict, optional
        Additional environment variables to set. If None, returns copy of
        current environment only.

    Returns
    -------
    dict
        Dictionary of environment variables suitable for subprocess.run(env=...).

    Examples
    --------
    >>> env = prepare_subprocess_env({"CUSTOM_VAR": "value"})
    >>> subprocess.run(["command"], env=env)

    >>> # Just copy current environment
    >>> env = prepare_subprocess_env()
    """
    env = os.environ.copy()

    if base_vars:
        env.update(base_vars)

    return env
