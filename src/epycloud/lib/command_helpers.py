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
get_docker_config : Extract Docker configuration with defaults
get_github_config : Extract GitHub configuration
get_batch_config : Extract Cloud Batch configuration
get_image_uri : Build full Docker image URI from config
get_github_pat : Get GitHub PAT from environment, secrets, or config
get_batch_service_account : Get batch service account email from terraform or default
generate_run_id : Generate a unique run ID
validate_inputs : Validate exp_id and run_id from args
"""

import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from epycloud.exceptions import CloudAPIError, ConfigError
from epycloud.lib.output import error, info


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
    When running from source (development):
        Assumes this file is at: project_root/src/epycloud/lib/command_helpers.py
        Navigates up 4 levels to reach project root.

    When installed as a tool:
        Uses current working directory as project root.
        This allows running build commands from the project directory.

    Examples
    --------
    >>> root = get_project_root()
    >>> terraform_dir = root / "terraform"
    >>> docker_dir = root / "docker"
    """
    # Try to detect if running from source or installed
    potential_root = Path(__file__).parent.parent.parent.parent

    # Check if this looks like a development setup (has pyproject.toml and docker/)
    if (potential_root / "pyproject.toml").exists() and (potential_root / "docker").exists():
        return potential_root

    # Otherwise, assume installed - use current working directory
    return Path.cwd()


def find_terraform_dir(terraform_dir: str | None = None) -> Path:
    """
    Find the terraform directory.

    Searches in the following order:
    1. Explicit path if provided via terraform_dir parameter
    2. Current working directory (./terraform)
    3. Package installation path (for development mode)

    Parameters
    ----------
    terraform_dir : str or None, optional
        Explicit path to terraform directory. If provided, this is used directly.

    Returns
    -------
    Path
        Absolute path to terraform directory.

    Raises
    ------
    FileNotFoundError
        If terraform directory cannot be found in any location.

    Examples
    --------
    >>> tf_dir = find_terraform_dir()
    >>> tf_dir = find_terraform_dir("/path/to/terraform")
    """
    # 1. Explicit path provided
    if terraform_dir:
        path = Path(terraform_dir).resolve()
        if path.exists() and path.is_dir():
            return path
        raise FileNotFoundError(f"Specified terraform directory not found: {path}")

    # 2. Current working directory
    cwd_terraform = Path.cwd() / "terraform"
    if cwd_terraform.exists() and cwd_terraform.is_dir():
        return cwd_terraform

    # 3. Package installation path (development mode)
    pkg_terraform = get_project_root() / "terraform"
    if pkg_terraform.exists() and pkg_terraform.is_dir():
        return pkg_terraform

    raise FileNotFoundError(
        "Terraform directory not found. Please either:\n"
        "  1. Run this command from the epymodelingsuite-cloud repository root, or\n"
        "  2. Specify the path with --terraform-dir /path/to/terraform"
    )


def check_docker_available() -> bool:
    """
    Check if Docker is available in the system PATH.

    Returns
    -------
    bool
        True if Docker is available, False otherwise.

    Notes
    -----
    Uses 'docker --version' to check availability. This is a lightweight
    check that doesn't require Docker daemon to be running.

    Examples
    --------
    >>> if not check_docker_available():
    ...     error("Docker is not installed or not in PATH")
    ...     return 1
    """
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


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
            "gcloud CLI not found. Install it from: https://cloud.google.com/sdk/docs/install"
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


def get_docker_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    Extract Docker configuration with defaults.

    Parameters
    ----------
    config : dict
        Configuration dictionary.

    Returns
    -------
    dict
        Dict with keys: registry, repo_name, image_name, image_tag

    Examples
    --------
    >>> docker = get_docker_config(config)
    >>> registry = docker["registry"]
    >>> image_name = docker["image_name"]
    """
    docker = config.get("docker", {})
    return {
        "registry": docker.get("registry", "us-central1-docker.pkg.dev"),
        "repo_name": docker.get("repo_name", "epymodelingsuite-repo"),
        "image_name": docker.get("image_name", "epymodelingsuite"),
        "image_tag": docker.get("image_tag", "latest"),
    }


def get_github_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    Extract GitHub configuration.

    Parameters
    ----------
    config : dict
        Configuration dictionary.

    Returns
    -------
    dict
        Dict with keys: forecast_repo, forecast_repo_ref, modeling_suite_repo,
                       modeling_suite_ref, personal_access_token

    Examples
    --------
    >>> github = get_github_config(config)
    >>> forecast_repo = github["forecast_repo"]
    >>> forecast_repo_ref = github["forecast_repo_ref"]
    >>> modeling_suite_repo = github["modeling_suite_repo"]
    """
    github = config.get("github", {})
    return {
        "forecast_repo": github.get("forecast_repo", ""),
        "forecast_repo_ref": github.get("forecast_repo_ref", ""),
        "modeling_suite_repo": github.get("modeling_suite_repo", ""),
        "modeling_suite_ref": github.get("modeling_suite_ref", "main"),
        "personal_access_token": github.get("personal_access_token", ""),
    }


def get_batch_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    Extract Cloud Batch configuration.

    Parameters
    ----------
    config : dict
        Configuration dictionary.

    Returns
    -------
    dict
        Full batch config dict with stage-specific settings

    Examples
    --------
    >>> batch_config = get_batch_config(config)
    >>> stage_a = batch_config.get("stage_a", {})
    """
    return config.get("google_cloud", {}).get("batch", {})


def get_image_uri(config: dict[str, Any], tag: str | None = None) -> str:
    """
    Build full Docker image URI from config.

    Parameters
    ----------
    config : dict
        Configuration dictionary.
    tag : str, optional
        Optional tag override (uses config default if None).

    Returns
    -------
    str
        Full image URI (e.g., "us-central1-docker.pkg.dev/project/repo/image:tag")

    Examples
    --------
    >>> image_uri = get_image_uri(config)
    >>> image_uri = get_image_uri(config, tag="v1.2.3")
    """
    docker = get_docker_config(config)
    google_cloud = config.get("google_cloud", {})
    project_id = google_cloud.get("project_id")

    image_tag = tag or docker["image_tag"]

    return (
        f"{docker['registry']}/"
        f"{project_id}/"
        f"{docker['repo_name']}/"
        f"{docker['image_name']}:{image_tag}"
    )


def get_github_pat(config: dict[str, Any], required: bool = False) -> str | None:
    """
    Get GitHub PAT from environment, secrets, or config.

    Priority:
    1. GITHUB_PAT environment variable
    2. EPYCLOUD_GITHUB_PAT environment variable
    3. github.personal_access_token from config

    Parameters
    ----------
    config : dict
        Configuration dictionary.
    required : bool, optional
        If True, print error and return None when not found, by default False.

    Returns
    -------
    str or None
        GitHub PAT or None if not found

    Examples
    --------
    >>> github_pat = get_github_pat(config)
    >>> github_pat = get_github_pat(config, required=True)
    """
    from epycloud.lib.paths import get_secrets_file

    # Try environment first
    github_pat = os.environ.get("GITHUB_PAT") or os.environ.get("EPYCLOUD_GITHUB_PAT")

    # Fall back to config
    if not github_pat:
        github_pat = config.get("github", {}).get("personal_access_token")

    # Handle required case
    if required and not github_pat:
        secrets_file = get_secrets_file()
        error("GitHub PAT required for this operation")
        info("Options:")
        info("  1. Set environment variable: export GITHUB_PAT=your_token")
        info("  2. Add to secrets.yaml: epycloud config edit-secrets")
        info(f"     (File location: {secrets_file})")
        return None

    return github_pat


def get_batch_service_account(project_id: str, project_root: Path | None = None) -> str:
    """
    Get batch service account email from terraform or default.

    Parameters
    ----------
    project_id : str
        Google Cloud project ID.
    project_root : Path, optional
        Optional project root (auto-detected if None).

    Returns
    -------
    str
        Batch service account email

    Examples
    --------
    >>> sa_email = get_batch_service_account(project_id)
    >>> sa_email = get_batch_service_account(project_id, project_root=Path("/path"))
    """
    if project_root is None:
        project_root = get_project_root()

    terraform_dir = project_root / "terraform"

    # Try getting from terraform output
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", "batch_service_account_email"],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fall back to default
    return f"batch-runtime@{project_id}.iam.gserviceaccount.com"


def generate_run_id() -> str:
    """
    Generate a unique run ID.

    Returns
    -------
    str
        Run ID in format: YYYYMMDD-HHMMSS-<uuid-prefix>

    Examples
    --------
    >>> run_id = generate_run_id()
    >>> # Returns something like: "20251115-143052-a1b2c3d4"
    """
    now = datetime.now()
    date_part = now.strftime("%Y%m%d")
    time_part = now.strftime("%H%M%S")
    unique_id = str(uuid4())[:8]
    return f"{date_part}-{time_part}-{unique_id}"


def validate_inputs(args: argparse.Namespace) -> tuple[str, str | None] | None:
    """
    Validate exp_id and run_id from args.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments.

    Returns
    -------
    tuple of (str, str or None) or None
        Tuple of (exp_id, run_id) on success, None on failure (error already printed)

    Examples
    --------
    >>> validated = validate_inputs(args)
    >>> if validated is None:
    ...     return 1
    >>> exp_id, run_id = validated
    """
    from epycloud.lib.validation import ValidationError, validate_exp_id, validate_run_id

    try:
        exp_id = validate_exp_id(args.exp_id)
        run_id = validate_run_id(args.run_id) if args.run_id else None
        return exp_id, run_id
    except ValidationError as e:
        error(str(e))
        return None
