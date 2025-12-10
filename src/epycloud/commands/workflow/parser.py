"""Parser configuration for workflow command."""

import argparse

from epycloud.lib.formatters import create_subparsers


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the workflow command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "workflow",
        help="Manage Cloud Workflows executions",
        description="List, describe, monitor, and manage workflow executions",
    )

    # Store parser for help printing
    parser.set_defaults(_workflow_parser=parser)

    # Create subcommands with consistent formatting
    workflow_subparsers = create_subparsers(parser, "workflow_subcommand")

    # ========== workflow list ==========
    list_parser = workflow_subparsers.add_parser(
        "list",
        help="List workflow executions",
    )

    list_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of executions to show (default: 20)",
    )

    list_parser.add_argument(
        "--status",
        choices=["ACTIVE", "SUCCEEDED", "FAILED", "CANCELLED"],
        help="Filter by status",
    )

    list_parser.add_argument(
        "--exp-id",
        help="Filter by experiment ID",
    )

    list_parser.add_argument(
        "--since",
        help="Show executions since (e.g., 24h, 7d, 30m)",
    )

    # ========== workflow describe ==========
    describe_parser = workflow_subparsers.add_parser(
        "describe",
        help="Describe execution details",
    )

    describe_parser.add_argument(
        "execution_id",
        help="Execution ID or full execution name",
    )

    # ========== workflow logs ==========
    logs_parser = workflow_subparsers.add_parser(
        "logs",
        help="Stream execution logs",
    )

    logs_parser.add_argument(
        "execution_id",
        help="Execution ID or full execution name",
    )

    logs_parser.add_argument(
        "--follow",
        "-f",
        action="store_true",
        help="Follow log output (stream mode)",
    )

    logs_parser.add_argument(
        "--tail",
        type=int,
        default=100,
        help="Show last N lines (default: 100)",
    )

    # ========== workflow cancel ==========
    cancel_parser = workflow_subparsers.add_parser(
        "cancel",
        help="Cancel running execution",
    )

    cancel_parser.add_argument(
        "execution_id",
        help="Execution ID or full execution name",
    )

    cancel_parser.add_argument(
        "--only-workflow",
        action="store_true",
        help="Cancel only the workflow execution, not child batch jobs (default: false)",
    )

    # ========== workflow retry ==========
    retry_parser = workflow_subparsers.add_parser(
        "retry",
        help="Retry failed execution",
    )

    retry_parser.add_argument(
        "execution_id",
        help="Execution ID or full execution name",
    )
