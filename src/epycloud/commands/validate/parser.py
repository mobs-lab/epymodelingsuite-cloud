"""Validate command parser."""

import argparse
from pathlib import Path


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the validate command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "validate",
        help="Validate experiment configuration",
        description="Validate experiment configuration using epymodelingsuite. "
        "Can validate from GitHub repository or local path.",
    )

    # Either exp-id (remote) or path (local) is required
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--exp-id",
        help="Experiment ID to validate from GitHub repository",
    )
    group.add_argument(
        "--path",
        type=Path,
        help="Path to local config directory (e.g., ./local/forecast/experiments/test-sim/config)",
    )

    parser.add_argument(
        "--format",
        choices=["text", "json", "yaml"],
        default="text",
        help="Output format: text|json|yaml (default: text)",
    )

    parser.add_argument(
        "--github-token",
        help="GitHub PAT for remote validation (or use from config/secrets/env)",
    )
