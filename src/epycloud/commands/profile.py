"""Profile management commands."""

import os
import subprocess
import sys
from typing import Any

import yaml

from epycloud.lib.output import error, info, success, warning
from epycloud.lib.paths import (
    get_active_profile_file,
    get_config_dir,
    get_profile_file,
)


def register_parser(subparsers: Any) -> None:
    """Register profile command parser.

    Args:
        subparsers: Subparsers from main argument parser
    """
    parser = subparsers.add_parser("profile", help="Profile management")
    # Store parser for help printing
    parser.set_defaults(_profile_parser=parser)
    profile_subparsers = parser.add_subparsers(
        dest="profile_subcommand", help="Profile subcommands"
    )

    # profile list
    profile_subparsers.add_parser("list", help="List all profiles")

    # profile use
    use_parser = profile_subparsers.add_parser("use", help="Activate a profile")
    use_parser.add_argument("name", help="Profile name to activate")

    # profile current
    profile_subparsers.add_parser("current", help="Show active profile")

    # profile create
    create_parser = profile_subparsers.add_parser("create", help="Create new profile")
    create_parser.add_argument("name", help="Profile name")
    create_parser.add_argument(
        "--template", choices=["basic", "full"], default="basic", help="Template to use"
    )
    create_parser.add_argument("--description", help="Profile description")
    create_parser.add_argument("--forecast-repo", help="GitHub forecast repository")

    # profile edit
    edit_parser = profile_subparsers.add_parser("edit", help="Edit profile config")
    edit_parser.add_argument("name", help="Profile name")

    # profile show
    show_parser = profile_subparsers.add_parser("show", help="Show profile details")
    show_parser.add_argument("name", help="Profile name")

    # profile delete
    delete_parser = profile_subparsers.add_parser("delete", help="Delete profile")
    delete_parser.add_argument("name", help="Profile name")


def handle(ctx: dict) -> int:
    """Handle profile command.

    Args:
        ctx: Command context

    Returns:
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

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    profiles_dir = get_config_dir() / "profiles"
    if not profiles_dir.exists():
        error("Profiles directory not found. Run 'epycloud config init' first.")
        return 1

    # Get all profile files
    profile_files = sorted(profiles_dir.glob("*.yaml"))
    if not profile_files:
        warning("No profiles found")
        info("Create a profile with: epycloud profile create <name>")
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

    if active_profile:
        info(f"\nActive: {active_profile} (*)")
    else:
        warning("\nNo active profile set")
        info("Activate a profile with: epycloud profile use <name>")

    return 0


def handle_use(ctx: dict) -> int:
    """Activate a profile.

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    args = ctx["args"]
    profile_name = args.name

    # Check if profile exists
    profile_file = get_profile_file(profile_name)
    if not profile_file.exists():
        error(f"Profile not found: {profile_name}")
        info("List available profiles with: epycloud profile list")
        return 1

    # Set active profile
    active_profile_file = get_active_profile_file()
    active_profile_file.write_text(f"{profile_name}\n")

    success(f"Activated profile: {profile_name}")
    return 0


def handle_current(ctx: dict) -> int:
    """Show active profile.

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    active_profile_file = get_active_profile_file()

    if not active_profile_file.exists():
        warning("No active profile set")
        info("Activate a profile with: epycloud profile use <name>")
        return 1

    active_profile = active_profile_file.read_text().strip()
    print(active_profile)
    return 0


def handle_create(ctx: dict) -> int:
    """Create new profile.

    Args:
        ctx: Command context

    Returns:
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

    Args:
        ctx: Command context

    Returns:
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
        info("Set EDITOR environment variable")
        return 1


def handle_show(ctx: dict) -> int:
    """Show profile details.

    Args:
        ctx: Command context

    Returns:
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

    Args:
        ctx: Command context

    Returns:
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
            info("Switch to another profile first with: epycloud profile use <name>")
            return 1

    # Delete profile file
    profile_file.unlink()
    success(f"Deleted profile: {profile_name}")

    return 0
