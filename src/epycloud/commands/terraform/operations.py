"""Terraform operations and helper functions."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from epycloud.lib.command_helpers import find_terraform_dir
from epycloud.lib.output import error, info


def _get_terraform_machine_type(stage_config: dict[str, Any]) -> str | None:
    """Return the first configured candidate for Terraform's legacy defaults."""
    machine_types = stage_config.get("machine_types")
    if isinstance(machine_types, list) and machine_types:
        first = machine_types[0]
        return first if isinstance(first, str) else None
    machine_type = stage_config.get("machine_type")
    return machine_type if isinstance(machine_type, str) else None


def get_terraform_env_vars(config: dict[str, Any]) -> dict[str, str]:
    """Build TF_VAR_* environment variables from config.

    Parameters
    ----------
    config : dict[str, Any]
        Configuration dict

    Returns
    -------
    dict[str, str]
        Dictionary of environment variables
    """
    env_vars = {}

    # Get configuration sections
    google_cloud_config = config.get("google_cloud", {})
    docker_config = config.get("docker", {})
    github_config = config.get("github", {})
    batch_config = google_cloud_config.get("batch", {})

    # Basic variables
    if "project_id" in google_cloud_config:
        env_vars["TF_VAR_project_id"] = google_cloud_config["project_id"]

    if "region" in google_cloud_config:
        env_vars["TF_VAR_region"] = google_cloud_config["region"]

    if "batch_regions" in google_cloud_config:
        env_vars["TF_VAR_batch_regions"] = json.dumps(
            google_cloud_config["batch_regions"], sort_keys=True
        )

    if "bucket_name" in google_cloud_config:
        env_vars["TF_VAR_bucket_name"] = google_cloud_config["bucket_name"]

    # Production workflow name. Terraform derives the staging workflow as
    # "<workflow_name>-staging", so running terraform under --env staging (where
    # workflow_name is already the staging name) is rejected by an HCL validation
    # rather than silently renaming the production workflow.
    if google_cloud_config.get("workflow_name"):
        env_vars["TF_VAR_workflow_name"] = google_cloud_config["workflow_name"]

    # Docker variables
    if "repo_name" in docker_config:
        env_vars["TF_VAR_repo_name"] = docker_config["repo_name"]

    if "image_name" in docker_config:
        env_vars["TF_VAR_image_name"] = docker_config["image_name"]

    if "image_tag" in docker_config:
        env_vars["TF_VAR_image_tag"] = docker_config["image_tag"]

    # GitHub variables
    if "forecast_repo" in github_config:
        env_vars["TF_VAR_github_forecast_repo"] = github_config["forecast_repo"]

    # Batch configuration
    if "task_count_per_node" in batch_config:
        env_vars["TF_VAR_task_count_per_node"] = str(batch_config["task_count_per_node"])

    # Stage A configuration
    stage_a_config = batch_config.get("stage_a", {})
    if "cpu_milli" in stage_a_config:
        env_vars["TF_VAR_stage_a_cpu_milli"] = str(stage_a_config["cpu_milli"])
    if "memory_mib" in stage_a_config:
        env_vars["TF_VAR_stage_a_memory_mib"] = str(stage_a_config["memory_mib"])
    stage_a_machine_type = _get_terraform_machine_type(stage_a_config)
    if stage_a_machine_type is not None:
        env_vars["TF_VAR_stage_a_machine_type"] = stage_a_machine_type
    if "max_run_duration" in stage_a_config:
        env_vars["TF_VAR_stage_a_max_run_duration"] = str(stage_a_config["max_run_duration"])

    # Stage B configuration
    stage_b_config = batch_config.get("stage_b", {})
    if "cpu_milli" in stage_b_config:
        env_vars["TF_VAR_stage_b_cpu_milli"] = str(stage_b_config["cpu_milli"])
    if "memory_mib" in stage_b_config:
        env_vars["TF_VAR_stage_b_memory_mib"] = str(stage_b_config["memory_mib"])
    stage_b_machine_type = _get_terraform_machine_type(stage_b_config)
    if stage_b_machine_type is not None:
        env_vars["TF_VAR_stage_b_machine_type"] = stage_b_machine_type
    if "max_run_duration" in stage_b_config:
        env_vars["TF_VAR_stage_b_max_run_duration"] = str(stage_b_config["max_run_duration"])

    # Stage C configuration
    stage_c_config = batch_config.get("stage_c", {})
    if "cpu_milli" in stage_c_config:
        env_vars["TF_VAR_stage_c_cpu_milli"] = str(stage_c_config["cpu_milli"])
    if "memory_mib" in stage_c_config:
        env_vars["TF_VAR_stage_c_memory_mib"] = str(stage_c_config["memory_mib"])
    stage_c_machine_type = _get_terraform_machine_type(stage_c_config)
    if stage_c_machine_type is not None:
        env_vars["TF_VAR_stage_c_machine_type"] = stage_c_machine_type
    if "max_run_duration" in stage_c_config:
        env_vars["TF_VAR_stage_c_max_run_duration"] = str(stage_c_config["max_run_duration"])
    if "run_output_stage" in stage_c_config:
        # Convert boolean to string for terraform
        env_vars["TF_VAR_run_output_stage"] = str(stage_c_config["run_output_stage"]).lower()

    return env_vars


def run_terraform_command(
    cmd: list[str],
    terraform_dir: Path,
    env_vars: dict[str, str],
    verbose: bool,
) -> int:
    """Run a terraform command.

    Parameters
    ----------
    cmd : list[str]
        Command to run
    terraform_dir : Path
        Working directory
    env_vars : dict[str, str]
        Environment variables
    verbose : bool
        Verbose output

    Returns
    -------
    int
        Exit code
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=terraform_dir,
            env={**os.environ, **env_vars},
            check=False,
        )

        return result.returncode

    except FileNotFoundError:
        error("terraform command not found. Please install Terraform:")
        info("  https://www.terraform.io/downloads.html")
        return 1
    except Exception as e:
        error(f"Failed to run terraform command: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def get_terraform_directory(terraform_dir_arg: str | None) -> Path | None:
    """Get terraform directory path.

    Parameters
    ----------
    terraform_dir_arg : str | None
        Optional override path

    Returns
    -------
    Path | None
        Terraform directory path, or None if not found
    """
    try:
        return find_terraform_dir(terraform_dir_arg)
    except FileNotFoundError as e:
        error(str(e))
        return None
