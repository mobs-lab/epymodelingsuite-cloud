"""Main CLI entry point for epycloud."""

import argparse
import sys
from pathlib import Path

from epycloud import __version__
from epycloud.config.loader import ConfigLoader
from epycloud.lib.output import error, info
from epycloud.lib.paths import ensure_config_dir


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all commands.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        prog="epycloud",
        description="Epidemic modeling pipeline management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument(
        "--version", "-v", action="version", version=f"epycloud {__version__}"
    )
    parser.add_argument(
        "--env",
        "-e",
        choices=["dev", "prod", "local"],
        default="dev",
        help="Environment: dev|prod|local (default: dev)",
    )
    parser.add_argument(
        "--profile", help="Override active profile (flu, covid, rsv, etc.)"
    )
    parser.add_argument(
        "--config", "-c", type=Path, help="Config file path (default: auto-detect)"
    )
    parser.add_argument(
        "--project-dir",
        "-d",
        type=Path,
        help="Project directory (default: current directory)",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode (errors only)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Import and register command parsers
    from epycloud.commands import config_cmd, profile

    config_cmd.register_parser(subparsers)
    profile.register_parser(subparsers)

    return parser


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args()

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
    if args.command != "config" or (hasattr(args, "config_subcommand") and args.config_subcommand != "init"):
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
