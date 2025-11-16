"""Terraform command for infrastructure management.

Available subcommands:
    epycloud terraform init     Initialize Terraform
    epycloud terraform plan     Plan infrastructure changes
    epycloud terraform apply    Apply infrastructure changes
    epycloud terraform destroy  Destroy infrastructure
    epycloud terraform output   Show Terraform outputs
    epycloud tf                 Alias for 'terraform'
"""

import argparse
import os
import subprocess
from typing import Any

from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import (
    get_project_root,
    handle_dry_run,
    require_config,
)
from epycloud.lib.formatters import create_subparsers
from epycloud.lib.output import ask_confirmation, error, info, success, warning


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the terraform command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "terraform",
        aliases=["tf"],
        help="Manage infrastructure with Terraform",
        description="Initialize, plan, apply, destroy, and view Terraform infrastructure",
    )

    # Store parser for help printing
    parser.set_defaults(_terraform_parser=parser)

    # Create subcommands with consistent formatting
    tf_subparsers = create_subparsers(parser, "terraform_subcommand")

    # ========== terraform init ==========
    tf_subparsers.add_parser(
        "init",
        help="Initialize Terraform",
    )

    # ========== terraform plan ==========
    plan_parser = tf_subparsers.add_parser(
        "plan",
        help="Plan infrastructure changes",
    )

    plan_parser.add_argument(
        "--target",
        help="Target specific resource (e.g., google_storage_bucket.data_bucket)",
    )

    # ========== terraform apply ==========
    apply_parser = tf_subparsers.add_parser(
        "apply",
        help="Apply infrastructure changes",
    )

    apply_parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip confirmation prompt",
    )

    apply_parser.add_argument(
        "--target",
        help="Target specific resource",
    )

    # ========== terraform destroy ==========
    destroy_parser = tf_subparsers.add_parser(
        "destroy",
        help="Destroy infrastructure",
    )

    destroy_parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip confirmation prompt",
    )

    destroy_parser.add_argument(
        "--target",
        help="Target specific resource",
    )

    # ========== terraform output ==========
    output_parser = tf_subparsers.add_parser(
        "output",
        help="Show Terraform outputs",
    )

    output_parser.add_argument(
        "name",
        nargs="?",
        help="Specific output name (optional)",
    )


def handle(ctx: dict[str, Any]) -> int:
    """Handle terraform command.

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

    try:
        require_config(ctx)
    except ConfigError as e:
        error(str(e))
        return 2

    if not args.terraform_subcommand:
        # Print help instead of error message
        if hasattr(args, "_terraform_parser"):
            args._terraform_parser.print_help()
        else:
            error("No subcommand specified. Use 'epycloud terraform --help'")
        return 1

    # Route to subcommand handler
    if args.terraform_subcommand == "init":
        return _handle_init(ctx)
    elif args.terraform_subcommand == "plan":
        return _handle_plan(ctx)
    elif args.terraform_subcommand == "apply":
        return _handle_apply(ctx)
    elif args.terraform_subcommand == "destroy":
        return _handle_destroy(ctx)
    elif args.terraform_subcommand == "output":
        return _handle_output(ctx)
    else:
        error(f"Unknown subcommand: {args.terraform_subcommand}")
        return 1


def _handle_init(ctx: dict[str, Any]) -> int:
    """Handle terraform init command.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context

    Returns
    -------
    int
        Exit code
    """
    config = ctx["config"]
    verbose = ctx["verbose"]
    ctx["dry_run"]

    info("Initializing Terraform...")

    # Get terraform directory
    project_root = get_project_root()
    terraform_dir = project_root / "terraform"

    if not terraform_dir.exists():
        error(f"Terraform directory not found: {terraform_dir}")
        return 1

    # Get environment variables from config
    env_vars = _get_terraform_env_vars(config)

    if handle_dry_run(
        ctx,
        "Run terraform init",
        {"working_directory": str(terraform_dir), "env_vars": env_vars},
    ):
        return 0

    # Run terraform init
    cmd = ["terraform", "init"]

    try:
        result = subprocess.run(
            cmd,
            cwd=terraform_dir,
            env={**os.environ, **env_vars},
            check=False,
        )

        if result.returncode == 0:
            success("Terraform initialized successfully")
            return 0
        else:
            error("Terraform initialization failed")
            return 1

    except FileNotFoundError:
        error("terraform command not found. Please install Terraform:")
        info("  https://www.terraform.io/downloads.html")
        return 1
    except Exception as e:
        error(f"Failed to run terraform init: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _handle_plan(ctx: dict[str, Any]) -> int:
    """Handle terraform plan command.

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
    config = ctx["config"]
    verbose = ctx["verbose"]
    ctx["dry_run"]

    info("Planning infrastructure changes...")

    # Get terraform directory
    project_root = get_project_root()
    terraform_dir = project_root / "terraform"

    if not terraform_dir.exists():
        error(f"Terraform directory not found: {terraform_dir}")
        return 1

    # Get environment variables from config
    env_vars = _get_terraform_env_vars(config)

    # Build command
    cmd = ["terraform", "plan"]

    if hasattr(args, "target") and args.target:
        cmd.extend(["-target", args.target])
        info(f"Targeting: {args.target}")

    if handle_dry_run(
        ctx,
        f"Run {' '.join(cmd)}",
        {"working_directory": str(terraform_dir), "env_vars": env_vars},
    ):
        return 0

    # Run terraform plan
    try:
        result = subprocess.run(
            cmd,
            cwd=terraform_dir,
            env={**os.environ, **env_vars},
            check=False,
        )

        if result.returncode == 0:
            success("Plan completed successfully")
            return 0
        else:
            error("Plan failed")
            return 1

    except FileNotFoundError:
        error("terraform command not found. Please install Terraform:")
        info("  https://www.terraform.io/downloads.html")
        return 1
    except Exception as e:
        error(f"Failed to run terraform plan: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _handle_apply(ctx: dict[str, Any]) -> int:
    """Handle terraform apply command.

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
    config = ctx["config"]
    environment = ctx["environment"]
    verbose = ctx["verbose"]
    dry_run = ctx["dry_run"]

    info("Applying infrastructure changes...")
    info(f"Environment: {environment}")

    # Confirmation for production
    if environment == "prod" and not args.auto_approve and not dry_run:
        warning("You are about to apply changes to PRODUCTION infrastructure")
        if not ask_confirmation("Are you sure you want to continue?", default=False):
            info("Apply cancelled")
            return 0

    # Get terraform directory
    project_root = get_project_root()
    terraform_dir = project_root / "terraform"

    if not terraform_dir.exists():
        error(f"Terraform directory not found: {terraform_dir}")
        return 1

    # Get environment variables from config
    env_vars = _get_terraform_env_vars(config)

    # Build command
    cmd = ["terraform", "apply"]

    if args.auto_approve:
        cmd.append("-auto-approve")

    if hasattr(args, "target") and args.target:
        cmd.extend(["-target", args.target])
        info(f"Targeting: {args.target}")

    if handle_dry_run(
        ctx,
        f"Run {' '.join(cmd)}",
        {"working_directory": str(terraform_dir), "env_vars": env_vars},
    ):
        return 0

    # Run terraform apply
    try:
        result = subprocess.run(
            cmd,
            cwd=terraform_dir,
            env={**os.environ, **env_vars},
            check=False,
        )

        if result.returncode == 0:
            success("Infrastructure changes applied successfully")
            return 0
        else:
            error("Apply failed")
            return 1

    except FileNotFoundError:
        error("terraform command not found. Please install Terraform:")
        info("  https://www.terraform.io/downloads.html")
        return 1
    except Exception as e:
        error(f"Failed to run terraform apply: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _handle_destroy(ctx: dict[str, Any]) -> int:
    """Handle terraform destroy command.

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
    config = ctx["config"]
    environment = ctx["environment"]
    verbose = ctx["verbose"]
    dry_run = ctx["dry_run"]

    warning("Destroying infrastructure...")
    info(f"Environment: {environment}")

    # Always require confirmation for destroy (unless auto-approve or dry-run)
    if not args.auto_approve and not dry_run:
        if environment == "prod":
            error("Destroying PRODUCTION infrastructure")
            warning("This will DELETE all infrastructure resources")
        else:
            warning(f"This will DELETE all infrastructure resources in {environment}")

        if not ask_confirmation("Are you ABSOLUTELY SURE you want to destroy?", default=False):
            info("Destroy cancelled")
            return 0

    # Get terraform directory
    project_root = get_project_root()
    terraform_dir = project_root / "terraform"

    if not terraform_dir.exists():
        error(f"Terraform directory not found: {terraform_dir}")
        return 1

    # Get environment variables from config
    env_vars = _get_terraform_env_vars(config)

    # Build command
    cmd = ["terraform", "destroy"]

    if args.auto_approve:
        cmd.append("-auto-approve")

    if hasattr(args, "target") and args.target:
        cmd.extend(["-target", args.target])
        info(f"Targeting: {args.target}")

    if handle_dry_run(
        ctx,
        f"Run {' '.join(cmd)}",
        {"working_directory": str(terraform_dir), "env_vars": env_vars},
    ):
        return 0

    # Run terraform destroy
    try:
        result = subprocess.run(
            cmd,
            cwd=terraform_dir,
            env={**os.environ, **env_vars},
            check=False,
        )

        if result.returncode == 0:
            success("Infrastructure destroyed successfully")
            return 0
        else:
            error("Destroy failed")
            return 1

    except FileNotFoundError:
        error("terraform command not found. Please install Terraform:")
        info("  https://www.terraform.io/downloads.html")
        return 1
    except Exception as e:
        error(f"Failed to run terraform destroy: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _handle_output(ctx: dict[str, Any]) -> int:
    """Handle terraform output command.

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
    config = ctx["config"]
    verbose = ctx["verbose"]
    ctx["dry_run"]

    # Get terraform directory
    project_root = get_project_root()
    terraform_dir = project_root / "terraform"

    if not terraform_dir.exists():
        error(f"Terraform directory not found: {terraform_dir}")
        return 1

    # Get environment variables from config
    env_vars = _get_terraform_env_vars(config)

    # Build command
    cmd = ["terraform", "output"]

    if hasattr(args, "name") and args.name:
        cmd.append(args.name)
        info(f"Getting output: {args.name}")
    else:
        info("Getting all outputs...")

    if handle_dry_run(
        ctx,
        f"Run {' '.join(cmd)}",
        {"working_directory": str(terraform_dir)},
    ):
        return 0

    # Run terraform output
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
        error(f"Failed to run terraform output: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _get_terraform_env_vars(config: dict[str, Any]) -> dict[str, str]:
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

    if "bucket_name" in google_cloud_config:
        env_vars["TF_VAR_bucket_name"] = google_cloud_config["bucket_name"]

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
    if "machine_type" in stage_a_config:
        env_vars["TF_VAR_stage_a_machine_type"] = stage_a_config["machine_type"]
    if "max_run_duration" in stage_a_config:
        env_vars["TF_VAR_stage_a_max_run_duration"] = str(stage_a_config["max_run_duration"])

    # Stage B configuration
    stage_b_config = batch_config.get("stage_b", {})
    if "cpu_milli" in stage_b_config:
        env_vars["TF_VAR_stage_b_cpu_milli"] = str(stage_b_config["cpu_milli"])
    if "memory_mib" in stage_b_config:
        env_vars["TF_VAR_stage_b_memory_mib"] = str(stage_b_config["memory_mib"])
    if "machine_type" in stage_b_config:
        env_vars["TF_VAR_stage_b_machine_type"] = stage_b_config["machine_type"]
    if "max_run_duration" in stage_b_config:
        env_vars["TF_VAR_stage_b_max_run_duration"] = str(stage_b_config["max_run_duration"])

    # Stage C configuration
    stage_c_config = batch_config.get("stage_c", {})
    if "cpu_milli" in stage_c_config:
        env_vars["TF_VAR_stage_c_cpu_milli"] = str(stage_c_config["cpu_milli"])
    if "memory_mib" in stage_c_config:
        env_vars["TF_VAR_stage_c_memory_mib"] = str(stage_c_config["memory_mib"])
    if "machine_type" in stage_c_config:
        env_vars["TF_VAR_stage_c_machine_type"] = stage_c_config["machine_type"]
    if "max_run_duration" in stage_c_config:
        env_vars["TF_VAR_stage_c_max_run_duration"] = str(stage_c_config["max_run_duration"])
    if "run_output_stage" in stage_c_config:
        # Convert boolean to string for terraform
        env_vars["TF_VAR_run_output_stage"] = str(stage_c_config["run_output_stage"]).lower()

    return env_vars
