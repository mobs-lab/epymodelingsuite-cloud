"""Argument parser for config command."""

from typing import Any

from epycloud.lib.formatters import CapitalizedHelpFormatter, create_subparsers


def register_parser(subparsers: Any) -> None:
    """Register config command parser.

    Parameters
    ----------
    subparsers : Any
        Subparsers from main argument parser
    """
    parser = subparsers.add_parser(
        "config",
        help="Configuration management",
        description="Manage configuration files and settings for epycloud CLI.",
        epilog="""Examples:
  epycloud config show
  epycloud config edit
  epycloud config get google_cloud.project_id
  epycloud config set google_cloud.project_id my-project
""",
        formatter_class=CapitalizedHelpFormatter,
    )
    # Store parser for help printing
    parser.set_defaults(_config_parser=parser)

    # Create subcommands with consistent formatting
    config_subparsers = create_subparsers(parser, "config_subcommand")

    # config init
    config_subparsers.add_parser("init", help="Initialize config directory")

    # config show
    show_parser = config_subparsers.add_parser("show", help="Show current configuration")
    show_parser.add_argument("--raw", action="store_true", help="Show raw YAML")

    # config edit
    edit_parser = config_subparsers.add_parser("edit", help="Edit base config in $EDITOR")
    edit_parser.add_argument(
        "--env", dest="edit_env", help="Edit environment config (dev, prod, local)"
    )

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

    # config list-envs
    config_subparsers.add_parser("list-envs", help="List available environments")
