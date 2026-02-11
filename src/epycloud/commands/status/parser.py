"""Status command parser."""

import argparse


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the status command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "status",
        help="Check pipeline status",
        description="Monitor active workflows and batch jobs",
    )

    parser.add_argument(
        "--exp-id",
        help="Filter by experiment ID",
    )

    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Watch mode (auto-refresh)",
    )

    parser.add_argument(
        "-r",
        "--recent",
        nargs="?",
        const="1h",
        default=None,
        metavar="TIME",
        help="Show recently completed items (e.g., 30m, 2h, 1d; default: 1h)",
    )

    parser.add_argument(
        "-n",
        "--interval",
        type=int,
        default=10,
        help="Refresh interval in seconds (default: 10)",
    )
