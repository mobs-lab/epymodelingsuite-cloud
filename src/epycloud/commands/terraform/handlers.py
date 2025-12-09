"""Handlers for terraform subcommands."""

from typing import Any

from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import handle_dry_run, require_config
from epycloud.lib.output import ask_confirmation, error, info, success, warning

from .operations import get_terraform_directory, get_terraform_env_vars, run_terraform_command


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
        return handle_init(ctx)
    elif args.terraform_subcommand == "plan":
        return handle_plan(ctx)
    elif args.terraform_subcommand == "apply":
        return handle_apply(ctx)
    elif args.terraform_subcommand == "destroy":
        return handle_destroy(ctx)
    elif args.terraform_subcommand == "output":
        return handle_output(ctx)
    else:
        error(f"Unknown subcommand: {args.terraform_subcommand}")
        return 1


def handle_init(ctx: dict[str, Any]) -> int:
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
    args = ctx["args"]
    config = ctx["config"]
    verbose = ctx["verbose"]

    info("Initializing Terraform...")

    # Get terraform directory
    terraform_dir_arg = getattr(args, "terraform_dir", None)
    terraform_dir = get_terraform_directory(terraform_dir_arg)
    if not terraform_dir:
        return 1

    info(f"Using terraform directory: {terraform_dir}")

    # Get environment variables from config
    env_vars = get_terraform_env_vars(config)

    if handle_dry_run(
        ctx,
        "Run terraform init",
        {"working_directory": str(terraform_dir), "env_vars": env_vars},
    ):
        return 0

    # Run terraform init
    cmd = ["terraform", "init"]
    result = run_terraform_command(cmd, terraform_dir, env_vars, verbose)

    if result == 0:
        success("Terraform initialized successfully")

    return result


def handle_plan(ctx: dict[str, Any]) -> int:
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

    info("Planning infrastructure changes...")

    # Get terraform directory
    terraform_dir_arg = getattr(args, "terraform_dir", None)
    terraform_dir = get_terraform_directory(terraform_dir_arg)
    if not terraform_dir:
        return 1

    info(f"Using terraform directory: {terraform_dir}")

    # Get environment variables from config
    env_vars = get_terraform_env_vars(config)

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
    result = run_terraform_command(cmd, terraform_dir, env_vars, verbose)

    if result == 0:
        success("Plan completed successfully")
    else:
        error("Plan failed")

    return result


def handle_apply(ctx: dict[str, Any]) -> int:
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
    terraform_dir_arg = getattr(args, "terraform_dir", None)
    terraform_dir = get_terraform_directory(terraform_dir_arg)
    if not terraform_dir:
        return 1

    info(f"Using terraform directory: {terraform_dir}")

    # Get environment variables from config
    env_vars = get_terraform_env_vars(config)

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
    result = run_terraform_command(cmd, terraform_dir, env_vars, verbose)

    if result == 0:
        success("Infrastructure changes applied successfully")
    else:
        error("Apply failed")

    return result


def handle_destroy(ctx: dict[str, Any]) -> int:
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
    terraform_dir_arg = getattr(args, "terraform_dir", None)
    terraform_dir = get_terraform_directory(terraform_dir_arg)
    if not terraform_dir:
        return 1

    info(f"Using terraform directory: {terraform_dir}")

    # Get environment variables from config
    env_vars = get_terraform_env_vars(config)

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
    result = run_terraform_command(cmd, terraform_dir, env_vars, verbose)

    if result == 0:
        success("Infrastructure destroyed successfully")
    else:
        error("Destroy failed")

    return result


def handle_output(ctx: dict[str, Any]) -> int:
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

    # Get terraform directory
    terraform_dir_arg = getattr(args, "terraform_dir", None)
    terraform_dir = get_terraform_directory(terraform_dir_arg)
    if not terraform_dir:
        return 1

    # Get environment variables from config
    env_vars = get_terraform_env_vars(config)

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
    return run_terraform_command(cmd, terraform_dir, env_vars, verbose)
