"""Main CLI entry point for epycloud."""

import argparse
import sys
from pathlib import Path

from epycloud import __version__
from epycloud.config.loader import ConfigLoader
from epycloud.lib.formatters import CapitalizedHelpFormatter
from epycloud.lib.output import error, info, set_color_enabled
from epycloud.lib.paths import ensure_config_dir


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser with all commands and subcommands.

    Configures the main argument parser with global options and registers
    all command-specific subparsers for the epycloud CLI.

    Returns
    -------
    argparse.ArgumentParser
        Configured argument parser with all commands registered.
    """
    parser = argparse.ArgumentParser(
        prog="epycloud",
        description="CLI tool to run epymodelingsuite workflow on Google Cloud",
        formatter_class=CapitalizedHelpFormatter,
    )

    # Global options
    parser.add_argument("--version", "-v", action="version", version=f"epycloud {__version__}")
    parser.add_argument(
        "--env",
        "-e",
        choices=["dev", "prod", "local"],
        default="dev",
        help="Environment: dev|prod|local (default: dev)",
    )
    parser.add_argument("--profile", help="Override active profile (flu, covid, rsv, etc.)")
    parser.add_argument("--config", "-c", type=Path, help="Config file path (default: auto-detect)")
    parser.add_argument(
        "--project-dir",
        "-d",
        type=Path,
        help="Project directory (default: current directory)",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode (errors only)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    # Customize main parser options title
    parser._optionals.title = "Options"

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Monkey-patch add_parser to automatically set Options title and formatter
    original_add_parser = subparsers.add_parser

    def custom_add_parser(*args, **kwargs):
        # Use CapitalizedHelpFormatter if no formatter_class specified
        if "formatter_class" not in kwargs:
            kwargs["formatter_class"] = CapitalizedHelpFormatter
        subparser = original_add_parser(*args, **kwargs)
        subparser._optionals.title = "Options"
        return subparser

    subparsers.add_parser = custom_add_parser

    # Import and register command parsers
    from epycloud.commands import (
        build,
        config_cmd,
        logs,
        profile,
        run,
        status,
        terraform,
        validate,
        workflow,
    )

    config_cmd.register_parser(subparsers)
    profile.register_parser(subparsers)
    build.register_parser(subparsers)
    run.register_parser(subparsers)
    workflow.register_parser(subparsers)
    terraform.register_parser(subparsers)
    validate.register_parser(subparsers)
    status.register_parser(subparsers)
    logs.register_parser(subparsers)

    return parser


def main() -> int:
    """
    Main CLI entry point for the epycloud command.

    Parses command-line arguments, loads configuration, creates command context,
    and routes execution to the appropriate command handler.

    Returns
    -------
    int
        Exit code: 0 for success, 1 for command failure, 2 for configuration error,
        130 for keyboard interrupt.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Apply defaults for arguments that might be None due to subparser issues
    if args.env is None:
        args.env = "dev"

    # Set color preference based on flag
    if args.no_color:
        set_color_enabled(False)

    # If no command provided, show help
    if not args.command:
        parser.print_help()
        return 1

    # Ensure config directory exists
    try:
        ensure_config_dir()
    except Exception as e:
        error(f"Failed to create config directory: {e}")
        return 2

    # Load configuration (unless it's config init)
    config = None
    if args.command != "config" or (
        hasattr(args, "config_subcommand") and args.config_subcommand != "init"
    ):
        try:
            config_loader = ConfigLoader(
                environment=args.env,
                profile=args.profile,
                config_path=args.config,
            )
            config = config_loader.load()
        except Exception as e:
            if args.verbose:
                import traceback

                traceback.print_exc()
            error(f"Failed to load configuration: {e}")
            info("Run 'epycloud config init' to initialize configuration")
            return 2

    # Create context for commands
    ctx = {
        "config": config,
        "environment": args.env,
        "profile": args.profile or (config.get("_meta", {}).get("profile") if config else None),
        "verbose": args.verbose,
        "quiet": args.quiet,
        "dry_run": args.dry_run,
        "args": args,
    }

    # Route to command handler
    try:
        if args.command == "config":
            from epycloud.commands import config_cmd

            return config_cmd.handle(ctx)
        elif args.command == "profile":
            from epycloud.commands import profile

            return profile.handle(ctx)
        elif args.command == "build":
            from epycloud.commands import build

            return build.handle(ctx)
        elif args.command == "run":
            from epycloud.commands import run

            return run.handle(ctx)
        elif args.command == "workflow":
            from epycloud.commands import workflow

            return workflow.handle(ctx)
        elif args.command == "terraform" or args.command == "tf":
            from epycloud.commands import terraform

            return terraform.handle(ctx)
        elif args.command == "validate":
            from epycloud.commands import validate

            return validate.handle(ctx)
        elif args.command == "status":
            from epycloud.commands import status

            return status.handle(ctx)
        elif args.command == "logs":
            from epycloud.commands import logs

            return logs.handle(ctx)
        else:
            error(f"Command '{args.command}' not yet implemented")
            return 1

    except KeyboardInterrupt:
        print()
        return 130
    except Exception as e:
        error(f"Command failed: {e}")
        if ctx["verbose"]:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
