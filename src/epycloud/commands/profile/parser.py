"""Profile command parser."""

from typing import Any

from epycloud.lib.formatters import create_subparsers


def register_parser(subparsers: Any) -> None:
    """Register profile command parser.

    Parameters
    ----------
    subparsers : Any
        Subparsers from main argument parser
    """
    parser = subparsers.add_parser("profile", help="Profile management")
    # Store parser for help printing
    parser.set_defaults(_profile_parser=parser)

    # Create subcommands with consistent formatting
    profile_subparsers = create_subparsers(parser, "profile_subcommand")

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
