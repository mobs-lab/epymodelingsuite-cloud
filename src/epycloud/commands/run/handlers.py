"""Top-level handlers for run command."""

from pathlib import Path
from typing import Any

from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import get_project_root, require_config, validate_inputs
from epycloud.lib.output import error, info

from .cloud.job import run_job_cloud
from .cloud.workflow import run_workflow_cloud
from .local.job import run_job_local
from .local.workflow import run_workflow_local


def handle(ctx: dict[str, Any]) -> int:
    """Handle the run command.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context with config and args

    Returns
    -------
    int
        Exit code (0 for success)
    """
    args = ctx["args"]

    if not hasattr(args, "run_subcommand") or not args.run_subcommand:
        # Print help instead of error message
        if hasattr(args, "_run_parser"):
            args._run_parser.print_help()
        else:
            error("Please specify a subcommand: 'workflow' or 'job'")
            info("Usage: epycloud run workflow --exp-id ID")
            info("       epycloud run job --stage STAGE --exp-id ID")
        return 1

    if args.run_subcommand == "workflow":
        return handle_workflow(ctx)
    elif args.run_subcommand == "job":
        return handle_job(ctx)
    else:
        error(f"Unknown subcommand: {args.run_subcommand}")
        return 1


def handle_workflow(ctx: dict[str, Any]) -> int:
    """Handle workflow execution.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    verbose = ctx["verbose"]
    dry_run = ctx["dry_run"]

    # Validate configuration
    try:
        config = require_config(ctx)
    except ConfigError as e:
        error(str(e))
        return 2

    # Validate inputs
    validated = validate_inputs(args)
    if validated is None:
        return 1
    exp_id, run_id = validated

    local = args.local
    skip_output = args.skip_output
    max_parallelism = args.max_parallelism
    task_count_per_node = getattr(args, "task_count_per_node", None)
    stage_a_machine_type_override = getattr(args, "stage_a_machine_type", None)
    stage_b_machine_type_override = getattr(args, "stage_b_machine_type", None)
    stage_c_machine_type_override = getattr(args, "stage_c_machine_type", None)
    forecast_repo_ref_override = getattr(args, "forecast_repo_ref", None)
    output_config = getattr(args, "output_config", None)
    wait = args.wait
    auto_confirm = args.yes
    project_directory = getattr(args, "project_directory", None)

    if local:
        # Resolve project directory
        if project_directory:
            project_dir_path = Path(project_directory).resolve()
        else:
            project_dir_path = get_project_root()

        return run_workflow_local(
            ctx=ctx,
            config=config,
            exp_id=exp_id,
            run_id=run_id,
            skip_output=skip_output,
            output_config=output_config,
            auto_confirm=auto_confirm,
            verbose=verbose,
            dry_run=dry_run,
            project_directory=project_dir_path,
        )
    else:
        return run_workflow_cloud(
            ctx=ctx,
            config=config,
            exp_id=exp_id,
            run_id=run_id,
            skip_output=skip_output,
            output_config=output_config,
            max_parallelism=max_parallelism,
            task_count_per_node=task_count_per_node,
            stage_a_machine_type_override=stage_a_machine_type_override,
            stage_b_machine_type_override=stage_b_machine_type_override,
            stage_c_machine_type_override=stage_c_machine_type_override,
            forecast_repo_ref_override=forecast_repo_ref_override,
            wait=wait,
            auto_confirm=auto_confirm,
            verbose=verbose,
            dry_run=dry_run,
        )


def handle_job(ctx: dict[str, Any]) -> int:
    """Handle individual job execution.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    verbose = ctx["verbose"]
    dry_run = ctx["dry_run"]

    # Validate configuration
    try:
        config = require_config(ctx)
    except ConfigError as e:
        error(str(e))
        return 2

    # Normalize stage name
    stage = args.stage.upper()
    if stage == "BUILDER":
        stage = "A"
    elif stage == "RUNNER":
        stage = "B"
    elif stage == "OUTPUT":
        stage = "C"

    # Validate inputs
    validated = validate_inputs(args)
    if validated is None:
        return 1
    exp_id, run_id = validated

    task_index = args.task_index
    num_tasks = args.num_tasks
    local = args.local
    wait = args.wait
    auto_confirm = args.yes
    machine_type_override = getattr(args, "machine_type", None)
    task_count_per_node = getattr(args, "task_count_per_node", None)
    project_directory = getattr(args, "project_directory", None)
    output_config = getattr(args, "output_config", None)

    # Validate requirements
    if stage in ["B", "C"] and not run_id:
        error(f"Stage {stage} requires --run-id")
        return 1

    if stage == "C" and not num_tasks:
        error("Stage C requires --num-tasks")
        return 1

    if local:
        # Resolve project directory
        if project_directory:
            project_dir_path = Path(project_directory).resolve()
        else:
            project_dir_path = get_project_root()

        return run_job_local(
            ctx=ctx,
            config=config,
            stage=stage,
            exp_id=exp_id,
            run_id=run_id,
            task_index=task_index,
            num_tasks=num_tasks,
            output_config=output_config,
            auto_confirm=auto_confirm,
            verbose=verbose,
            dry_run=dry_run,
            project_directory=project_dir_path,
        )
    else:
        return run_job_cloud(
            ctx=ctx,
            config=config,
            stage=stage,
            exp_id=exp_id,
            run_id=run_id,
            task_index=task_index,
            num_tasks=num_tasks,
            output_config=output_config,
            machine_type_override=machine_type_override,
            task_count_per_node=task_count_per_node,
            wait=wait,
            auto_confirm=auto_confirm,
            verbose=verbose,
            dry_run=dry_run,
        )
