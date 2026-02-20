"""Profile command handlers."""

import os
import subprocess
import sys

import yaml

from epycloud.lib.output import error, info, status, success, warning
from epycloud.lib.paths import (
    _list_yaml_files,
    get_active_profile_file,
    get_config_dir,
    get_profile_file,
)


def handle(ctx: dict) -> int:
    """Handle profile command.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    subcommand = args.profile_subcommand

    if not subcommand:
        # Print help instead of error message
        if hasattr(args, "_profile_parser"):
            args._profile_parser.print_help()
        else:
            error("No subcommand provided. Use 'epycloud profile --help' for usage.")
        return 1

    if subcommand == "list":
        return handle_list(ctx)
    elif subcommand == "use":
        return handle_use(ctx)
    elif subcommand == "current":
        return handle_current(ctx)
    elif subcommand == "create":
        return handle_create(ctx)
    elif subcommand == "edit":
        return handle_edit(ctx)
    elif subcommand == "show":
        return handle_show(ctx)
    elif subcommand == "delete":
        return handle_delete(ctx)
    else:
        error(f"Unknown subcommand: {subcommand}")
        return 1


def handle_list(ctx: dict) -> int:
    """List all profiles.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
        Exit code
    """
    profiles_dir = get_config_dir() / "profiles"
    if not profiles_dir.exists():
        error("Profiles directory not found. Run 'epycloud config init' first.")
        return 1

    # Get all profile files (.yaml and .yml, deduplicated)
    profile_files = _list_yaml_files(profiles_dir)
    if not profile_files:
        warning("No profiles found")
        status("Create a profile with: epycloud profile create <name>")
        return 0

    # Get active profile
    active_profile_file = get_active_profile_file()
    active_profile = None
    if active_profile_file.exists():
        active_profile = active_profile_file.read_text().strip()

    # List profiles
    info("Available profiles:")
    for profile_file in profile_files:
        profile_name = profile_file.stem

        # Load profile to get description
        with open(profile_file) as f:
            profile_data = yaml.safe_load(f) or {}

        description = profile_data.get("description", "No description")

        # Mark active profile
        if profile_name == active_profile:
            success(f"  {profile_name} (*) - {description}")
        else:
            info(f"  {profile_name} - {description}")

    print()  # Blank line before
    if active_profile:
        info(f"Active: {active_profile} (*)")
    else:
        warning("No active profile set")
        status("Activate a profile with: epycloud profile use <name>")

    return 0


def handle_use(ctx: dict) -> int:
    """Activate a profile.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    profile_name = args.name

    # Check if profile exists
    profile_file = get_profile_file(profile_name)
    if not profile_file.exists():
        error(f"Profile not found: {profile_name}")
        status("List available profiles with: epycloud profile list")
        return 1

    # Set active profile
    active_profile_file = get_active_profile_file()
    active_profile_file.write_text(f"{profile_name}\n")

    success(f"Activated profile: {profile_name}")
    return 0


def handle_current(ctx: dict) -> int:
    """Show active profile.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
        Exit code
    """
    active_profile_file = get_active_profile_file()

    if not active_profile_file.exists():
        warning("No active profile set")
        status("Activate a profile with: epycloud profile use <name>")
        return 1

    active_profile = active_profile_file.read_text().strip()
    print(active_profile)
    return 0


def handle_create(ctx: dict) -> int:
    """Create new profile.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    profile_name = args.name

    # Check if profile already exists
    profile_file = get_profile_file(profile_name)
    if profile_file.exists():
        error(f"Profile already exists: {profile_name}")
        return 1

    # Create profile based on template
    if args.template == "basic":
        profile_data = {
            "name": profile_name,
            "description": args.description or f"{profile_name} modeling",
            "github": {
                "forecast_repo": args.forecast_repo or f"mobs-lab/{profile_name}-forecast",
            },
        }
    else:  # full template
        profile_data = {
            "name": profile_name,
            "description": args.description or f"{profile_name} modeling",
            "github": {
                "forecast_repo": args.forecast_repo or f"mobs-lab/{profile_name}-forecast",
            },
            "google_cloud": {
                "batch": {
                    "stage_b": {
                        "cpu_milli": 2000,
                        "memory_mib": 8192,
                    },
                    "max_parallelism": 100,
                },
            },
        }

    # Ensure profiles directory exists
    profile_file.parent.mkdir(parents=True, exist_ok=True)

    # Write profile
    with open(profile_file, "w") as f:
        yaml.dump(profile_data, f, default_flow_style=False, sort_keys=False)

    success(f"Created profile: {profile_name}")
    info(f"Edit with: epycloud profile edit {profile_name}")
    info(f"Activate with: epycloud profile use {profile_name}")

    return 0


def handle_edit(ctx: dict) -> int:
    """Edit profile config.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    profile_name = args.name
    editor = os.environ.get("EDITOR", "vim")

    # Check if profile exists
    profile_file = get_profile_file(profile_name)
    if not profile_file.exists():
        error(f"Profile not found: {profile_name}")
        return 1

    # Open in editor
    try:
        subprocess.run([editor, str(profile_file)], check=True)
        success(f"Edited profile: {profile_name}")
        return 0
    except subprocess.CalledProcessError as e:
        error(f"Editor failed: {e}")
        return 1
    except FileNotFoundError:
        error(f"Editor not found: {editor}")
        status("Set EDITOR environment variable")
        return 1


def handle_show(ctx: dict) -> int:
    """Show profile details.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    profile_name = args.name

    # Check if profile exists
    profile_file = get_profile_file(profile_name)
    if not profile_file.exists():
        error(f"Profile not found: {profile_name}")
        return 1

    # Load and display profile
    with open(profile_file) as f:
        profile_data = yaml.safe_load(f) or {}

    info(f"Profile: {profile_name}")
    yaml.dump(profile_data, sys.stdout, default_flow_style=False, sort_keys=False)

    return 0


def handle_delete(ctx: dict) -> int:
    """Delete profile.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    profile_name = args.name

    # Check if profile exists
    profile_file = get_profile_file(profile_name)
    if not profile_file.exists():
        error(f"Profile not found: {profile_name}")
        return 1

    # Check if it's the active profile
    active_profile_file = get_active_profile_file()
    if active_profile_file.exists():
        active_profile = active_profile_file.read_text().strip()
        if active_profile == profile_name:
            warning(f"Cannot delete active profile: {profile_name}")
            status("Switch to another profile first with: epycloud profile use <name>")
            return 1

    # Delete profile file
    profile_file.unlink()
    success(f"Deleted profile: {profile_name}")

    return 0
