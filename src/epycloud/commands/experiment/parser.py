"""Parser configuration for experiment command."""

import argparse

from epycloud.lib.formatters import create_subparsers


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the experiment command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "experiment",
        help="Browse experiments and runs on GCS",
        description="List experiments and runs stored in Google Cloud Storage",
    )

    # Store parser for help printing
    parser.set_defaults(_experiment_parser=parser)

    # Create subcommands with consistent formatting
    experiment_subparsers = create_subparsers(parser, "experiment_subcommand")

    # ========== experiment list ==========
    list_parser = experiment_subparsers.add_parser(
        "list",
        help="List experiments and runs",
    )

    list_parser.add_argument(
        "-e",
        "--exp-filter",
        metavar="PATTERN",
        help=(
            "Glob pattern to filter experiment paths (fnmatch). "
            'Examples: "202607/*", "*smc*", "202607/ed_*"'
        ),
    )

    list_parser.add_argument(
        "--latest",
        action="store_true",
        help="Show only the latest run per experiment",
    )

    list_parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=50,
        help="Number of rows to show (default: 50, 0 for all)",
    )

    list_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["table", "uri", "args"],
        default="table",
        help="Output format: table (default), uri (gs:// paths), or args (--exp-id/--run-id flags)",
    )

    list_parser.add_argument(
        "--bucket",
        help="GCS bucket name (default: from epycloud config)",
    )

    list_parser.add_argument(
        "--dir-prefix",
        help='GCS directory prefix (default: from config or "pipeline/flu/")',
    )
