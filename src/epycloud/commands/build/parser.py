"""Parser configuration for build command."""

import argparse

from epycloud.lib.formatters import create_subparsers


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the build command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "build",
        help="Build and manage Docker images",
        description="Build Docker images and manage Cloud Build jobs",
    )

    # Store parser for help printing
    parser.set_defaults(_build_parser=parser)

    # Create subcommands with consistent formatting
    build_subparsers = create_subparsers(parser, "build_subcommand")

    # epycloud build cloud
    cloud_parser = build_subparsers.add_parser(
        "cloud",
        help="Submit to Cloud Build (async)",
        description="Build with Cloud Build (async by default)",
    )
    cloud_parser.add_argument(
        "--cache",
        action="store_true",
        help="Enable build cache (cache disabled by default)",
    )
    cloud_parser.add_argument(
        "--tag",
        help="Image tag (default: from config)",
    )
    cloud_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for build to complete",
    )
    cloud_parser.add_argument(
        "-f",
        "--file",
        dest="dockerfile",
        help="Path to Dockerfile (default: docker/Dockerfile)",
    )
    cloud_parser.add_argument(
        "context",
        nargs="?",
        help="Build context directory (default: project root)",
    )

    # epycloud build local
    local_parser = build_subparsers.add_parser(
        "local",
        help="Build locally and push to registry",
        description="Build locally and push to Artifact Registry",
    )
    local_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable build cache",
    )
    local_parser.add_argument(
        "--tag",
        help="Image tag (default: from config)",
    )
    local_parser.add_argument(
        "--no-push",
        action="store_true",
        help="Don't push to registry",
    )
    local_parser.add_argument(
        "-f",
        "--file",
        dest="dockerfile",
        help="Path to Dockerfile (default: docker/Dockerfile)",
    )
    local_parser.add_argument(
        "context",
        nargs="?",
        help="Build context directory (default: docker/)",
    )

    # epycloud build dev
    dev_parser = build_subparsers.add_parser(
        "dev",
        help="Build locally only (no push)",
        description="Build local development image (no push by default)",
    )
    dev_parser.add_argument(
        "--cache",
        action="store_true",
        help="Enable build cache (cache disabled by default)",
    )
    dev_parser.add_argument(
        "--tag",
        help="Image tag (default: from config)",
    )
    dev_parser.add_argument(
        "--push",
        action="store_true",
        help="Push to registry",
    )
    dev_parser.add_argument(
        "-f",
        "--file",
        dest="dockerfile",
        help="Path to Dockerfile (default: docker/Dockerfile)",
    )
    dev_parser.add_argument(
        "context",
        nargs="?",
        help="Build context directory (default: docker/)",
    )

    # epycloud build status
    status_parser = build_subparsers.add_parser(
        "status",
        help="Display recent/ongoing Cloud Build jobs",
        description="Display recent/ongoing Cloud Build jobs",
    )
    status_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of builds to display (default: 10)",
    )
    status_parser.add_argument(
        "--ongoing",
        action="store_true",
        help="Show only active builds (QUEUED, WORKING)",
    )
