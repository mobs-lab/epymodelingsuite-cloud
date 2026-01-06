"""Argument parser registration for run command."""

import argparse

from epycloud.lib.formatters import CapitalizedHelpFormatter, create_subparsers


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the run command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "run",
        help="Execute pipeline stages or workflows",
        description="Run pipeline workflows (complete A→B→C execution) or individual stages/jobs.",
        epilog="""Examples:
  epycloud run workflow --exp-id my-experiment
  epycloud run job --stage A --exp-id my-experiment
  epycloud run job --stage B --exp-id my-exp --run-id <run_id> --task-index 0
""",
        formatter_class=CapitalizedHelpFormatter,
    )

    # Store parser for help printing
    parser.set_defaults(_run_parser=parser)

    # Create subcommands with consistent formatting
    run_subparsers = create_subparsers(parser, "run_subcommand")

    # ========== run workflow ==========
    workflow_parser = run_subparsers.add_parser(
        "workflow",
        help="Submit complete workflow (all stages: A → B → C)",
    )

    workflow_parser.add_argument(
        "--exp-id",
        required=True,
        help="Experiment ID (required)",
    )

    workflow_parser.add_argument(
        "--run-id",
        help="Run ID (auto-generated if not provided)",
    )

    workflow_parser.add_argument(
        "--local",
        action="store_true",
        help="Run locally with docker compose instead of cloud",
    )

    workflow_parser.add_argument(
        "--skip-output",
        action="store_true",
        help="Skip stage C (output generation)",
    )

    workflow_parser.add_argument(
        "--max-parallelism",
        type=int,
        help="Max parallel tasks (default: from config)",
    )

    workflow_parser.add_argument(
        "--stage-a-machine-type",
        help="Override Stage A machine type (auto-sets CPU/memory to machine max)",
    )

    workflow_parser.add_argument(
        "--stage-b-machine-type",
        help="Override Stage B machine type (auto-sets CPU/memory to machine max)",
    )

    workflow_parser.add_argument(
        "--stage-c-machine-type",
        help="Override Stage C machine type (auto-sets CPU/memory to machine max)",
    )

    workflow_parser.add_argument(
        "--task-count-per-node",
        type=int,
        help="Max tasks per VM node (1 = dedicated VM per task, default: from config)",
    )

    workflow_parser.add_argument(
        "--forecast-repo-ref",
        help="Override forecast repo branch/tag/commit (default: from config)",
    )

    workflow_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for completion and stream logs",
    )

    workflow_parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-confirm without prompting",
    )

    workflow_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing",
    )

    workflow_parser.add_argument(
        "--project-directory",
        help="Docker Compose project directory (default: auto-detected)",
    )

    workflow_parser.add_argument(
        "--output-config",
        help="Output config filename for Stage C (e.g., output_projection.yaml). Uses auto-detection if not specified.",
    )

    # ========== run job ==========
    job_parser = run_subparsers.add_parser(
        "job",
        help="Run a single stage or task",
    )

    job_parser.add_argument(
        "--stage",
        required=True,
        choices=["A", "B", "C", "builder", "runner", "output"],
        help="Stage to run: A|B|C|builder|runner|output",
    )

    job_parser.add_argument(
        "--exp-id",
        required=True,
        help="Experiment ID (required)",
    )

    job_parser.add_argument(
        "--run-id",
        help="Run ID (required for stages B and C, auto-generated for stage A)",
    )

    job_parser.add_argument(
        "--task-index",
        type=int,
        default=0,
        help="Task index for stage B (default: 0)",
    )

    job_parser.add_argument(
        "--num-tasks",
        type=int,
        help="Number of tasks (required for stage C)",
    )

    job_parser.add_argument(
        "--machine-type",
        help="Override machine type for this job (auto-sets CPU/memory to machine max)",
    )

    job_parser.add_argument(
        "--task-count-per-node",
        type=int,
        help="Max tasks per VM node (1 = dedicated VM per task, default: from config)",
    )

    job_parser.add_argument(
        "--local",
        action="store_true",
        help="Run locally with docker compose instead of cloud",
    )

    job_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for completion and stream logs",
    )

    job_parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-confirm without prompting",
    )

    job_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing",
    )

    job_parser.add_argument(
        "--project-directory",
        help="Docker Compose project directory (default: auto-detected)",
    )

    job_parser.add_argument(
        "--output-config",
        help="Output config filename for Stage C (e.g., output_projection.yaml). Uses auto-detection if not specified.",
    )
