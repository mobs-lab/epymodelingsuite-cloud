"""Argument parser for logs command."""

import argparse


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the logs command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "logs",
        help="View pipeline logs",
        description="View logs from Cloud Batch jobs and workflow executions",
    )

    parser.add_argument(
        "--exp-id",
        help="Experiment ID (required unless --job-name or --execution-id is specified)",
    )

    parser.add_argument(
        "--run-id",
        help="Run ID (optional, shows all runs if not specified)",
    )

    parser.add_argument(
        "--stage",
        choices=["A", "B", "C", "builder", "runner", "output"],
        help="Stage to view logs for: A|B|C|builder|runner|output",
    )

    parser.add_argument(
        "--task-index",
        type=int,
        help="Task index for stage B (default: all tasks)",
    )

    parser.add_argument(
        "--job-name",
        help="Batch job name (e.g., stage-b-003a2da6)",
    )

    parser.add_argument(
        "--execution-id",
        help="Workflow execution ID (filters all stages from that execution)",
    )

    parser.add_argument(
        "--follow",
        "-f",
        action="store_true",
        help="Follow mode (stream logs)",
    )

    parser.add_argument(
        "--tail",
        type=int,
        default=100,
        help="Show last N lines (default: 100, use 0 for unlimited)",
    )

    parser.add_argument(
        "--since",
        help="Show logs since (e.g., 1h, 30m, 24h)",
    )

    parser.add_argument(
        "--level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Filter by log level",
    )
