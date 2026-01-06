"""Argument parser for terraform command."""

import argparse

from epycloud.lib.formatters import create_subparsers


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the terraform command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "terraform",
        aliases=["tf"],
        help="Manage infrastructure with Terraform",
        description="Initialize, plan, apply, destroy, and view Terraform infrastructure",
    )

    # Store parser for help printing
    parser.set_defaults(_terraform_parser=parser)

    # Common terraform options
    parser.add_argument(
        "--terraform-dir",
        metavar="DIR",
        help="Path to terraform directory (default: ./terraform or package location)",
    )

    # Create subcommands with consistent formatting
    tf_subparsers = create_subparsers(parser, "terraform_subcommand")

    # ========== terraform init ==========
    tf_subparsers.add_parser(
        "init",
        help="Initialize Terraform",
    )

    # ========== terraform plan ==========
    plan_parser = tf_subparsers.add_parser(
        "plan",
        help="Plan infrastructure changes",
    )

    plan_parser.add_argument(
        "--target",
        help="Target specific resource (e.g., google_storage_bucket.data_bucket)",
    )

    # ========== terraform apply ==========
    apply_parser = tf_subparsers.add_parser(
        "apply",
        help="Apply infrastructure changes",
    )

    apply_parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip confirmation prompt",
    )

    apply_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing",
    )

    apply_parser.add_argument(
        "--target",
        help="Target specific resource",
    )

    # ========== terraform destroy ==========
    destroy_parser = tf_subparsers.add_parser(
        "destroy",
        help="Destroy infrastructure",
    )

    destroy_parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip confirmation prompt",
    )

    destroy_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing",
    )

    destroy_parser.add_argument(
        "--target",
        help="Target specific resource",
    )

    # ========== terraform output ==========
    output_parser = tf_subparsers.add_parser(
        "output",
        help="Show Terraform outputs",
    )

    output_parser.add_argument(
        "name",
        nargs="?",
        help="Specific output name (optional)",
    )
