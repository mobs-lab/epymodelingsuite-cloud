"""Docker Compose runner for local execution."""

import subprocess
from pathlib import Path

from epycloud.lib.command_helpers import (
    check_docker_available,
    handle_dry_run,
    prepare_subprocess_env,
)
from epycloud.lib.output import error, info


def run_docker_compose_stage(
    project_directory: Path,
    service: str,
    env_vars: dict[str, str],
    dry_run: bool,
) -> int:
    """Run a docker compose service.

    Parameters
    ----------
    project_directory : Path
        Absolute path to Docker Compose project directory
    service : str
        Service name (builder, runner, output)
    env_vars : dict[str, str]
        Environment variables
    dry_run : bool
        Dry run mode

    Returns
    -------
    int
        Exit code
    """
    # Check Docker availability
    if not dry_run and not check_docker_available():
        error("Docker is not installed or not in PATH")
        info("Install Docker Engine or OrbStack (macOS)")
        return 1

    # Use --project-directory to specify compose file location (no chdir needed)
    cmd = [
        "docker",
        "compose",
        "--project-directory",
        str(project_directory),
        "run",
        "--rm",
        service,
    ]

    if handle_dry_run(
        {"dry_run": dry_run},
        f"Run Docker Compose service '{service}'",
        {"command": " ".join(cmd), "env_vars": str(env_vars)},
    ):
        return 0

    # Set environment variables for subprocess
    env = prepare_subprocess_env(env_vars)

    # Execute command (no directory change needed)
    result = subprocess.run(cmd, env=env, check=False)
    return result.returncode


def build_env_from_config(config: dict) -> dict[str, str]:
    """Build environment variables from configuration.

    Extracts all necessary configuration values and converts them to
    environment variables suitable for Docker Compose.

    Parameters
    ----------
    config : dict
        Configuration dict

    Returns
    -------
    dict[str, str]
        Dictionary of environment variables
    """
    google_cloud = config.get("google_cloud", {})
    github = config.get("github", {})
    storage = config.get("storage", {})
    logging_config = config.get("logging", {})

    env = {
        # Google Cloud
        "PROJECT_ID": google_cloud.get("project_id", ""),
        "REGION": google_cloud.get("region", ""),
        "BUCKET_NAME": google_cloud.get("bucket_name", ""),
        # GitHub (include PAT from secrets if present)
        "GITHUB_FORECAST_REPO": github.get("forecast_repo", ""),
        "GITHUB_MODELING_SUITE_REPO": github.get("modeling_suite_repo", ""),
        "GITHUB_MODELING_SUITE_REF": github.get("modeling_suite_ref", "main"),
        "GITHUB_PAT": github.get("personal_access_token", ""),
        # Storage
        "DIR_PREFIX": storage.get("dir_prefix", ""),
        # Logging
        "LOG_LEVEL": logging_config.get("level", "INFO"),
        "STORAGE_VERBOSE": str(logging_config.get("storage_verbose", True)).lower(),
    }

    return env
