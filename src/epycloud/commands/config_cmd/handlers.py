"""Handlers for config subcommands."""

import sys

import yaml

from epycloud.config.loader import ConfigLoader, get_config_value, set_config_value
from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import require_config
from epycloud.lib.output import error, info, print_dict, success, warning
from epycloud.lib.paths import get_config_dir, get_config_file, list_environments

from .operations import edit_config_file, edit_secrets_file, initialize_config_dir


def handle(ctx: dict) -> int:
    """Handle config command.

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
    elif subcommand == "list-envs":
        return handle_list_envs(ctx)
    else:
        error(f"Unknown subcommand: {subcommand}")
        return 1


def handle_init(ctx: dict) -> int:
    """Initialize config directory with templates.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
        Exit code
    """
    return initialize_config_dir()


def handle_show(ctx: dict) -> int:
    """Show current configuration.

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

        print()  # Blank line before
        print("Configuration:")
        print_dict(config)

        # Show sources
        sources = config.get("_meta", {}).get("config_sources", [])
        if sources:
            print()  # Blank line before
            print("Loaded from:")
            for source in sources:
                print(f"  - {source}")

    return 0


def handle_edit(ctx: dict) -> int:
    """Edit config file in $EDITOR.

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
    env = getattr(args, "edit_env", None) if hasattr(args, "edit_env") else None
    return edit_config_file(env=env)


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
    return edit_secrets_file()


def handle_validate(ctx: dict) -> int:
    """Validate configuration.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
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

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
        Exit code
    """
    print(get_config_dir())
    return 0


def handle_get(ctx: dict) -> int:
    """Get config value.

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
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

    Parameters
    ----------
    ctx : dict
        Command context

    Returns
    -------
    int
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


def handle_list_envs(ctx: dict) -> int:
    """List available environments.

    Parameters
    ----------
    ctx : dict
        Command context.

    Returns
    -------
    int
        Exit code (0 for success).
    """
    envs = list_environments()

    if not envs:
        info("No environments found")
        info(f"Environment files should be in: {get_config_dir() / 'environments'}")
        return 0

    # Get current environment from context
    current_env = ctx.get("environment", "dev")

    info("Available environments:")
    for env in envs:
        marker = " (current)" if env == current_env else ""
        print(f"  {env}{marker}")

    return 0
