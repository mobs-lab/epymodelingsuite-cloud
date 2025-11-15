"""Configuration management commands.

Available subcommands:
    epycloud config init          Initialize config directory
    epycloud config show          Show current configuration
    epycloud config edit          Edit base config in $EDITOR
    epycloud config edit-secrets  Edit secrets.yaml in $EDITOR
    epycloud config validate      Validate configuration
    epycloud config path          Show config directory path
    epycloud config get           Get config value
    epycloud config set           Set config value
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from epycloud.config.loader import ConfigLoader, get_config_value, set_config_value
from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import require_config
from epycloud.lib.output import error, info, print_dict, success, warning
from epycloud.lib.paths import (
    get_config_dir,
    get_config_file,
    get_environment_file,
    get_secrets_file,
)


def register_parser(subparsers: Any) -> None:
    """Register config command parser.

    Args:
        subparsers: Subparsers from main argument parser
    """
    parser = subparsers.add_parser(
        "config",
        help="Configuration management",
        description="""Manage configuration files and settings.

Examples:
  epycloud config show
  epycloud config edit
  epycloud config get google_cloud.project_id
  epycloud config set google_cloud.project_id my-project
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Store parser for help printing
    parser.set_defaults(_config_parser=parser)
    config_subparsers = parser.add_subparsers(
        dest="config_subcommand",
        help="",
        title="Subcommands",
    )

    # config init
    config_subparsers.add_parser("init", help="Initialize config directory")

    # config show
    show_parser = config_subparsers.add_parser("show", help="Show current configuration")
    show_parser.add_argument("--raw", action="store_true", help="Show raw YAML")

    # config edit
    edit_parser = config_subparsers.add_parser("edit", help="Edit base config in $EDITOR")
    edit_parser.add_argument("--env", dest="edit_env", help="Edit environment config (dev, prod, local)")

    # config edit-secrets
    config_subparsers.add_parser("edit-secrets", help="Edit secrets.yaml in $EDITOR")

    # config validate
    config_subparsers.add_parser("validate", help="Validate configuration")

    # config path
    config_subparsers.add_parser("path", help="Show config directory path")

    # config get
    get_parser = config_subparsers.add_parser("get", help="Get config value")
    get_parser.add_argument(
        "key", help="Config key in dot notation (e.g., google_cloud.project_id)"
    )

    # config set
    set_parser = config_subparsers.add_parser("set", help="Set config value")
    set_parser.add_argument("key", help="Config key in dot notation")
    set_parser.add_argument("value", help="Value to set")


def handle(ctx: dict) -> int:
    """Handle config command.

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    args = ctx["args"]
    subcommand = args.config_subcommand

    if not subcommand:
        # Print help instead of error message
        if hasattr(args, "_config_parser"):
            args._config_parser.print_help()
        else:
            error("No subcommand provided. Use 'epycloud config --help' for usage.")
        return 1

    if subcommand == "init":
        return handle_init(ctx)
    elif subcommand == "show":
        return handle_show(ctx)
    elif subcommand == "edit":
        return handle_edit(ctx)
    elif subcommand == "edit-secrets":
        return handle_edit_secrets(ctx)
    elif subcommand == "validate":
        return handle_validate(ctx)
    elif subcommand == "path":
        return handle_path(ctx)
    elif subcommand == "get":
        return handle_get(ctx)
    elif subcommand == "set":
        return handle_set(ctx)
    else:
        error(f"Unknown subcommand: {subcommand}")
        return 1


def handle_init(ctx: dict) -> int:
    """Initialize config directory with templates.

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    config_dir = get_config_dir()
    template_dir = Path(__file__).parent.parent / "config" / "templates"

    info(f"Initializing config directory: {config_dir}")

    # Create directories
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "environments").mkdir(exist_ok=True)
    (config_dir / "profiles").mkdir(exist_ok=True)

    # Copy templates
    templates = [
        ("config.yaml", config_dir / "config.yaml"),
        ("dev.yaml", config_dir / "environments" / "dev.yaml"),
        ("prod.yaml", config_dir / "environments" / "prod.yaml"),
        ("local.yaml", config_dir / "environments" / "local.yaml"),
        ("flu.yaml", config_dir / "profiles" / "flu.yaml"),
        ("secrets.yaml", config_dir / "secrets.yaml"),
    ]

    for template_name, dest_path in templates:
        template_path = template_dir / template_name

        if dest_path.exists():
            warning(f"Skipping {dest_path.name} (already exists)")
            continue

        shutil.copy(template_path, dest_path)
        success(f"Created {dest_path.name}")

        # Set secrets file permissions
        if dest_path.name == "secrets.yaml":
            os.chmod(dest_path, 0o600)
            info("  Set permissions to 0600")

    # Set default profile
    active_profile_file = config_dir / "active_profile"
    if not active_profile_file.exists():
        active_profile_file.write_text("flu\n")
        success("Set default profile to 'flu'")

    success(f"\nConfiguration initialized at {config_dir}")
    info("\nNext steps:")
    info("  1. Edit config.yaml with your GCP project settings")
    info("  2. Add your GitHub token to secrets.yaml")
    info("  3. Review environment configs in environments/")
    info("  4. Run 'epycloud config validate' to check configuration")

    return 0


def handle_show(ctx: dict) -> int:
    """Show current configuration.

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    args = ctx["args"]

    try:
        config = require_config(ctx)
    except ConfigError as e:
        error(str(e))
        return 1

    if args.raw:
        # Show raw YAML
        yaml.dump(config, sys.stdout, default_flow_style=False, sort_keys=False)
    else:
        # Show formatted
        print(f"Environment: {ctx['environment']}")

        # Show profile with metadata if available
        profile = config.get("_meta", {}).get("profile")
        if profile:
            print(f"Profile: {profile.get('name', ctx['profile'])}")
            if "description" in profile:
                print(f"  Description: {profile['description']}")
            if "version" in profile:
                print(f"  Version: {profile['version']}")
        else:
            print(f"Profile: {ctx['profile'] or '(none)'}")

        print("\nConfiguration:")
        print_dict(config)

        # Show sources
        sources = config.get("_meta", {}).get("config_sources", [])
        if sources:
            print("\nLoaded from:")
            for source in sources:
                print(f"  - {source}")

    return 0


def handle_edit(ctx: dict) -> int:
    """Edit config file in $EDITOR.

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    args = ctx["args"]
    editor = os.environ.get("EDITOR", "vim")

    # Determine which file to edit
    # Check if --env flag was explicitly provided to the edit subcommand
    if hasattr(args, "edit_env") and args.edit_env:
        file_path = get_environment_file(args.edit_env)
        if not file_path.exists():
            error(f"Environment config not found: {file_path}")
            return 1
    else:
        # Default: edit base config.yaml
        file_path = get_config_file()
        if not file_path.exists():
            error(f"Config file not found: {file_path}")
            info("Run 'epycloud config init' first")
            return 1

    # Open in editor
    try:
        subprocess.run([editor, str(file_path)], check=True)
        success(f"Edited {file_path}")
        return 0
    except subprocess.CalledProcessError as e:
        error(f"Editor failed: {e}")
        return 1
    except FileNotFoundError:
        error(f"Editor not found: {editor}")
        info("Set EDITOR environment variable or use 'epycloud config show'")
        return 1


def handle_edit_secrets(ctx: dict) -> int:
    """Edit secrets.yaml file in $EDITOR.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
        Exit code
    """
    editor = os.environ.get("EDITOR", "vim")
    file_path = get_secrets_file()

    # Create secrets file with secure permissions if it doesn't exist
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("# Secrets configuration\n# Store sensitive credentials here\n\ngithub:\n  personal_access_token: \"\"\n")
        os.chmod(file_path, 0o600)
        info(f"Created {file_path} with secure permissions (0600)")

    # Open in editor
    try:
        subprocess.run([editor, str(file_path)], check=True)
        success(f"Edited {file_path}")

        # Verify permissions after editing
        current_perms = file_path.stat().st_mode & 0o777
        if current_perms != 0o600:
            warning(f"Secrets file has insecure permissions: {oct(current_perms)}")
            info("Setting permissions to 0600...")
            os.chmod(file_path, 0o600)
            success("Permissions fixed")

        return 0
    except subprocess.CalledProcessError as e:
        error(f"Editor failed: {e}")
        return 1
    except FileNotFoundError:
        error(f"Editor not found: {editor}")
        info("Set EDITOR environment variable")
        return 1


def handle_validate(ctx: dict) -> int:
    """Validate configuration.

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    try:
        # Try to load config
        config_loader = ConfigLoader(
            environment=ctx["environment"],
            profile=ctx["profile"],
        )
        config = config_loader.load()

        # Basic validation
        errors = []
        warnings_list = []

        # Check required fields
        required_fields = [
            "google_cloud.project_id",
            "google_cloud.region",
            "google_cloud.bucket_name",
        ]

        for field in required_fields:
            value = get_config_value(config, field)
            if not value or (isinstance(value, str) and value.startswith("your-")):
                errors.append(f"Missing or placeholder value: {field}")

        # Check GitHub token
        github_token = get_config_value(config, "github.personal_access_token")
        if not github_token or (
            isinstance(github_token, str)
            and github_token
            in (
                "ghp_xxxxxxxxxxxxxxxxxxxx",
                "github_pat_xxxxxxxxxxxxxxxxxxxx",
            )
        ):
            warnings_list.append("GitHub token not configured in secrets.yaml")

        # Report results
        if errors:
            error("Configuration validation failed:")
            for err in errors:
                error(f"  - {err}")
            return 1
        elif warnings_list:
            success("Configuration is valid")
            warning("\nWarnings:")
            for warn in warnings_list:
                warning(f"  - {warn}")
            return 0
        else:
            success("Configuration is valid")
            return 0

    except Exception as e:
        error(f"Validation failed: {e}")
        if ctx["verbose"]:
            import traceback

            traceback.print_exc()
        return 1


def handle_path(ctx: dict) -> int:
    """Show config directory path.

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    print(get_config_dir())
    return 0


def handle_get(ctx: dict) -> int:
    """Get config value.

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    config = ctx["config"]
    args = ctx["args"]

    value = get_config_value(config, args.key)
    if value is None:
        error(f"Key not found: {args.key}")
        return 1

    print(value)
    return 0


def handle_set(ctx: dict) -> int:
    """Set config value.

    Args:
        ctx: Command context

    Returns:
        Exit code
    """
    config_file = get_config_file()

    if not config_file.exists():
        error("Config file not found. Run 'epycloud config init' first.")
        return 1

    # Load current config
    with open(config_file) as f:
        config = yaml.safe_load(f) or {}

    # Set value
    args = ctx["args"]
    set_config_value(config, args.key, args.value)

    # Save config
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    success(f"Set {args.key} = {args.value}")
    return 0
