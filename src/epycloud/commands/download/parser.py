"""Argument parser for download command."""

import argparse


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the download command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "download",
        help="Download output plots from GCS",
        description="Download specific output plots for experiments from Google Cloud Storage",
    )

    parser.add_argument(
        "-e",
        "--exp-filter",
        required=True,
        metavar="PATTERN",
        help=(
            "Glob pattern to match experiment paths (fnmatch). "
            'Auto-appends * if ends with /. Examples: "202606/", "202606/hosp_*"'
        ),
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        default="./downloads",
        help="Output directory (default: ./downloads)",
    )

    parser.add_argument(
        "--name-format",
        choices=["long", "short"],
        default="long",
        help="Filename format: long (GCS-path flattened, default) or short (basename only)",
    )

    parser.add_argument(
        "--nest-runs",
        action="store_true",
        help="Add {run_id}/ subdirectory under each experiment",
    )

    parser.add_argument(
        "--bucket",
        help="GCS bucket name (default: from epycloud config)",
    )

    parser.add_argument(
        "--dir-prefix",
        help='GCS directory prefix (default: from config or "pipeline/flu/")',
    )

    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
