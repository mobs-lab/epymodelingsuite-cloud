"""Run command for executing pipeline stages and workflows.

Available subcommands:
    epycloud run workflow    Submit complete workflow (all stages: A → B → C)
    epycloud run job         Run a single stage or task (A, B, or C)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import requests

from epycloud.exceptions import CloudAPIError, ConfigError, ValidationError
from epycloud.lib.command_helpers import (
    check_docker_available,
    generate_run_id,
    get_batch_config,
    get_batch_service_account,
    get_docker_config,
    get_gcloud_access_token,
    get_github_config,
    get_image_uri,
    get_project_root,
    handle_dry_run,
    prepare_subprocess_env,
    require_config,
    validate_inputs,
)
from epycloud.lib.formatters import CapitalizedHelpFormatter, create_subparsers
from epycloud.lib.output import error, info, success, warning
from epycloud.lib.validation import sanitize_label_value, validate_machine_type
from epycloud.utils.confirmation import format_confirmation, prompt_confirmation


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
        "--stage-b-machine-type",
        help="Override Stage B machine type (e.g., n2-standard-4, c2-standard-8)",
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
        "--project-directory",
        help="Docker Compose project directory (default: auto-detected)",
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
        "--project-directory",
        help="Docker Compose project directory (default: auto-detected)",
    )


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
        return _handle_workflow(ctx)
    elif args.run_subcommand == "job":
        return _handle_job(ctx)
    else:
        error(f"Unknown subcommand: {args.run_subcommand}")
        return 1


def _handle_workflow(ctx: dict[str, Any]) -> int:
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
    stage_b_machine_type_override = getattr(args, "stage_b_machine_type", None)
    wait = args.wait
    auto_confirm = args.yes
    project_directory = getattr(args, "project_directory", None)

    if local:
        # Resolve project directory
        if project_directory:
            project_dir_path = Path(project_directory).resolve()
        else:
            project_dir_path = get_project_root()

        return _run_workflow_local(
            ctx=ctx,
            config=config,
            exp_id=exp_id,
            run_id=run_id,
            skip_output=skip_output,
            auto_confirm=auto_confirm,
            verbose=verbose,
            dry_run=dry_run,
            project_directory=project_dir_path,
        )
    else:
        return _run_workflow_cloud(
            ctx=ctx,
            config=config,
            exp_id=exp_id,
            run_id=run_id,
            skip_output=skip_output,
            max_parallelism=max_parallelism,
            stage_b_machine_type_override=stage_b_machine_type_override,
            wait=wait,
            auto_confirm=auto_confirm,
            verbose=verbose,
            dry_run=dry_run,
        )


def _handle_job(ctx: dict[str, Any]) -> int:
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
    project_directory = getattr(args, "project_directory", None)

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

        return _run_job_local(
            ctx=ctx,
            config=config,
            stage=stage,
            exp_id=exp_id,
            run_id=run_id,
            task_index=task_index,
            num_tasks=num_tasks,
            auto_confirm=auto_confirm,
            verbose=verbose,
            dry_run=dry_run,
            project_directory=project_dir_path,
        )
    else:
        return _run_job_cloud(
            ctx=ctx,
            config=config,
            stage=stage,
            exp_id=exp_id,
            run_id=run_id,
            task_index=task_index,
            num_tasks=num_tasks,
            wait=wait,
            auto_confirm=auto_confirm,
            verbose=verbose,
            dry_run=dry_run,
        )


def _run_workflow_cloud(
    ctx: dict[str, Any],
    config: dict[str, Any],
    exp_id: str,
    run_id: str | None,
    skip_output: bool,
    max_parallelism: int | None,
    stage_b_machine_type_override: str | None,
    wait: bool,
    auto_confirm: bool,
    verbose: bool,
    dry_run: bool,
) -> int:
    """Submit workflow to Cloud Workflows.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context
    config : dict[str, Any]
        Configuration dict
    exp_id : str
        Experiment ID
    run_id : str | None
        Optional run ID (auto-generated in workflow if not provided)
    skip_output : bool
        Skip stage C
    max_parallelism : int | None
        Max parallel tasks
    stage_b_machine_type_override : str | None
        Override Stage B machine type (e.g., n2-standard-4)
    wait : bool
        Wait for completion
    auto_confirm : bool
        Auto-confirm without prompting
    verbose : bool
        Verbose output
    dry_run : bool
        Dry run mode

    Returns
    -------
    int
        Exit code
    """
    # Get config values
    google_cloud = config.get("google_cloud", {})
    project_id = google_cloud.get("project_id")
    region = google_cloud.get("region", "us-central1")
    bucket_name = google_cloud.get("bucket_name")
    pipeline = config.get("pipeline", {})
    dir_prefix = pipeline.get("dir_prefix", "pipeline/flu/")
    github = get_github_config(config)
    github_forecast_repo = github["forecast_repo"]
    batch_config = get_batch_config(config)

    if not max_parallelism:
        max_parallelism = pipeline.get("max_parallelism", 100)

    # Validate required config
    if not project_id:
        error("google_cloud.project_id not configured")
        return 2
    if not bucket_name:
        error("google_cloud.bucket_name not configured")
        return 2

    # Get batch service account email
    batch_sa_email = get_batch_service_account(project_id)

    # Build Docker image URI
    image_uri = get_image_uri(config)

    # Get Stage B machine type
    stage_b_config = batch_config.get("stage_b", {})
    stage_b_machine_type_default = stage_b_config.get("machine_type", "")
    # Use override if provided, otherwise fall back to config default
    stage_b_machine_type = stage_b_machine_type_override or stage_b_machine_type_default

    # Validate machine type override if provided
    if stage_b_machine_type_override:
        info(f"Validating machine type '{stage_b_machine_type_override}'...")
        try:
            validate_machine_type(stage_b_machine_type_override, project_id, region)
            success(f"Machine type '{stage_b_machine_type_override}' is valid")
        except ValidationError as e:
            error(str(e))
            return 1

    # Build storage path
    generated_run_id = run_id if run_id else "<auto-generated>"
    storage_path = f"gs://{bucket_name}/{dir_prefix}{exp_id}/{generated_run_id}/"

    # Build confirmation info
    confirmation_info = {
        "command_type": "workflow",
        "exp_id": exp_id,
        "run_id": generated_run_id,
        "environment": ctx.get("environment", ""),
        "profile": ctx.get("profile", ""),
        "project_id": project_id,
        "region": region,
        "bucket_name": bucket_name,
        "storage_path": storage_path,
        "modeling_suite_repo": github["modeling_suite_repo"],
        "modeling_suite_ref": github["modeling_suite_ref"],
        "forecast_repo": github_forecast_repo,
        "pat_configured": bool(github["personal_access_token"]),
        "max_parallelism": max_parallelism,
        "stage_b_machine_type": stage_b_machine_type,
        "stage_b_machine_type_override": stage_b_machine_type_override,
        "skip_output": skip_output,
        "image_uri": image_uri,
    }

    # Show confirmation and prompt
    confirmation_message = format_confirmation(confirmation_info, mode="cloud")
    if not prompt_confirmation(confirmation_message, auto_confirm=auto_confirm):
        info("Operation cancelled.")
        return 0

    info("Submitting workflow to Cloud Workflows...")

    # Build workflow argument
    workflow_arg = {
        "bucket": bucket_name,
        "dirPrefix": dir_prefix,
        "exp_id": exp_id,
        "githubForecastRepo": github_forecast_repo,
        "batchSaEmail": batch_sa_email,
    }

    if run_id:
        workflow_arg["runId"] = run_id

    if max_parallelism:
        workflow_arg["maxParallelism"] = max_parallelism

    if stage_b_machine_type_override:
        workflow_arg["stageBMachineType"] = stage_b_machine_type_override

    if skip_output:
        workflow_arg["runOutputStage"] = False

    # Get auth token
    try:
        access_token = get_gcloud_access_token(verbose=verbose)
    except CloudAPIError as e:
        error(str(e))
        return 1

    # Construct API URL
    workflow_url = (
        f"https://workflowexecutions.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/workflows/epymodelingsuite-pipeline/executions"
    )

    # Build request body
    request_body = {"argument": json.dumps(workflow_arg)}

    if handle_dry_run(
        {"dry_run": dry_run},
        "Submit workflow",
        {"url": workflow_url, "arguments": json.dumps(workflow_arg, indent=2)},
    ):
        return 0

    # Submit workflow
    try:
        response = requests.post(
            workflow_url,
            json=request_body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        result = response.json()
        execution_name = result.get("name", "")

        success("Workflow submitted successfully!")
        info(f"Execution: {execution_name}")
        print()

        # Extract execution ID from name
        execution_id = execution_name.split("/")[-1] if execution_name else ""

        if execution_id:
            info("Monitor with:")
            info(
                f"  gcloud workflows executions describe {execution_id} "
                f"--workflow=epymodelingsuite-pipeline --location={region}"
            )
            info(
                f"  gcloud workflows executions list epymodelingsuite-pipeline "
                f"--location={region}"
            )
            print()
            info("Or use:")
            info(f"  epycloud workflow describe {execution_id}")
            info(f"  epycloud workflow logs {execution_id} --follow")

        if wait:
            warning("--wait not yet implemented for workflows")
            info("Use: gcloud workflows executions describe --wait")

        return 0

    except requests.HTTPError as e:
        if e.response is not None:
            error(f"Failed to submit workflow: HTTP {e.response.status_code}")
            if verbose:
                print(e.response.text, file=sys.stderr)
        else:
            error("Failed to submit workflow: No response")
        return 1
    except requests.RequestException as e:
        api_error = CloudAPIError(
            "Network error while submitting workflow", api="Workflows", status_code=None
        )
        error(str(api_error))
        if verbose:
            print(f"Details: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Failed to submit workflow: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


def _run_workflow_local(
    ctx: dict[str, Any],
    config: dict[str, Any],
    exp_id: str,
    run_id: str | None,
    skip_output: bool,
    auto_confirm: bool,
    verbose: bool,
    dry_run: bool,
    project_directory: Path,
) -> int:
    """Run complete workflow locally with docker compose.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context
    config : dict[str, Any]
        Configuration dict
    exp_id : str
        Experiment ID
    run_id : str | None
        Optional run ID
    skip_output : bool
        Skip stage C
    auto_confirm : bool
        Auto-confirm without prompting
    verbose : bool
        Verbose output
    dry_run : bool
        Dry run mode
    project_directory : Path
        Absolute path to Docker Compose project directory

    Returns
    -------
    int
        Exit code
    """
    # Get config values
    docker = get_docker_config(config)
    image_name = docker["image_name"]
    image_tag = docker["image_tag"]
    pipeline = config.get("pipeline", {})
    dir_prefix = pipeline.get("dir_prefix", "pipeline/flu/")

    # Generate run ID if not provided
    if not run_id:
        run_id = generate_run_id()

    # Build storage path
    storage_path = f"./local/bucket/{dir_prefix}{exp_id}/{run_id}/"

    # Build confirmation info
    confirmation_info = {
        "command_type": "workflow",
        "exp_id": exp_id,
        "run_id": run_id,
        "environment": ctx.get("environment", ""),
        "profile": ctx.get("profile", ""),
        "storage_path": storage_path,
        "skip_output": skip_output,
        "image_name": image_name,
        "image_tag": image_tag,
    }

    # Show confirmation and prompt
    confirmation_message = format_confirmation(confirmation_info, mode="local")
    if not prompt_confirmation(confirmation_message, auto_confirm=auto_confirm):
        info("Operation cancelled.")
        return 0

    info("Running workflow locally with Docker Compose...")
    info(f"Experiment ID: {exp_id}")
    info(f"Run ID: {run_id}")
    info(f"Project directory: {project_directory}")

    # Stage A: Builder
    info("")
    info("=" * 60)
    info("Stage A: Builder (generating input files)")
    info("=" * 60)

    result = _run_docker_compose_stage(
        project_directory=project_directory,
        service="builder",
        env_vars={"EXP_ID": exp_id, "RUN_ID": run_id},
        dry_run=dry_run,
    )

    if result != 0:
        error("Stage A failed")
        return result

    success("Stage A completed successfully")

    # Detect number of tasks from builder artifacts
    bucket_path = project_directory / "local" / "bucket" / exp_id / run_id / "builder-artifacts"

    if not dry_run:
        if not bucket_path.exists():
            error(f"Builder artifacts not found: {bucket_path}")
            return 1

        input_files = list(bucket_path.glob("input_*.pkl"))
        num_tasks = len(input_files)

        if num_tasks == 0:
            error("No input files generated by builder")
            return 1

        info(f"Found {num_tasks} tasks to run")
    else:
        num_tasks = 10  # Dummy value for dry run

    # Stage B: Runner (all tasks)
    info("")
    info("=" * 60)
    info(f"Stage B: Runner (processing {num_tasks} tasks)")
    info("=" * 60)

    for task_idx in range(num_tasks):
        info(f"Running task {task_idx + 1}/{num_tasks}...")

        result = _run_docker_compose_stage(
            project_directory=project_directory,
            service="runner",
            env_vars={
                "EXP_ID": exp_id,
                "RUN_ID": run_id,
                "TASK_INDEX": str(task_idx),
            },
            dry_run=dry_run,
        )

        if result != 0:
            error(f"Task {task_idx} failed")
            return result

    success("Stage B completed successfully")

    # Stage C: Output (unless skipped)
    if not skip_output:
        info("")
        info("=" * 60)
        info("Stage C: Output (generating results)")
        info("=" * 60)

        result = _run_docker_compose_stage(
            project_directory=project_directory,
            service="output",
            env_vars={
                "EXP_ID": exp_id,
                "RUN_ID": run_id,
                "NUM_TASKS": str(num_tasks),
            },
            dry_run=dry_run,
        )

        if result != 0:
            error("Stage C failed")
            return result

        success("Stage C completed successfully")
    else:
        info("")
        info("Stage C skipped (--skip-output)")

    # Summary
    info("")
    info("=" * 60)
    success("Workflow completed successfully!")
    info("=" * 60)
    info(f"Results in: ./local/bucket/{exp_id}/{run_id}/")

    return 0


def _run_job_cloud(
    ctx: dict[str, Any],
    config: dict[str, Any],
    stage: str,
    exp_id: str,
    run_id: str | None,
    task_index: int,
    num_tasks: int | None,
    wait: bool,
    auto_confirm: bool,
    verbose: bool,
    dry_run: bool,
) -> int:
    """Submit individual job to Cloud Batch.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context
    config : dict[str, Any]
        Configuration dict
    stage : str
        Stage (A, B, or C)
    exp_id : str
        Experiment ID
    run_id : str | None
        Run ID
    task_index : int
        Task index for stage B
    num_tasks : int | None
        Number of tasks for stage C
    wait : bool
        Wait for completion
    auto_confirm : bool
        Auto-confirm without prompting
    verbose : bool
        Verbose output
    dry_run : bool
        Dry run mode

    Returns
    -------
    int
        Exit code
    """
    # Get configuration
    google_cloud = config.get("google_cloud", {})
    project_id = google_cloud.get("project_id")
    region = google_cloud.get("region", "us-central1")
    bucket_name = google_cloud.get("bucket_name")
    pipeline = config.get("pipeline", {})
    dir_prefix = pipeline.get("dir_prefix", "pipeline/flu/")
    batch_config = get_batch_config(config)
    github = get_github_config(config)
    github_forecast_repo = github["forecast_repo"]

    # Get image info
    image_uri = get_image_uri(config)

    # Get stage-specific resources
    stage_key = f"stage_{stage.lower()}"
    stage_config = batch_config.get(stage_key, {})
    cpu_milli = stage_config.get("cpu_milli", 2000)
    memory_mib = stage_config.get("memory_mib", 8192)
    machine_type = stage_config.get("machine_type", "")
    max_run_duration = stage_config.get("max_run_duration", 3600)

    # Validate
    if not project_id or not bucket_name:
        error("Missing required configuration: project_id or bucket_name")
        return 2

    # Get batch service account
    batch_sa_email = get_batch_service_account(project_id)

    # Generate job ID
    timestamp = int(time.time())
    job_id = f"epy-{timestamp}-stage-{stage.lower()}-manual"

    # Auto-generate run_id for stage A if not provided
    if stage == "A" and not run_id:
        run_id = generate_run_id()

    # Build confirmation info
    confirmation_info = {
        "command_type": "job",
        "exp_id": exp_id,
        "run_id": run_id if run_id else "<auto-generated>",
        "environment": ctx.get("environment", ""),
        "profile": ctx.get("profile", ""),
        "project_id": project_id,
        "region": region,
        "stage": stage,
        "machine_type": machine_type,
        "max_duration_hours": max_run_duration // 3600,
        "image_uri": image_uri,
    }

    if stage == "B":
        confirmation_info["task_index"] = task_index
    elif stage == "C":
        confirmation_info["num_tasks"] = num_tasks

    # Show confirmation and prompt
    confirmation_message = format_confirmation(confirmation_info, mode="cloud")
    if not prompt_confirmation(confirmation_message, auto_confirm=auto_confirm):
        info("Operation cancelled.")
        return 0

    info(f"Submitting Stage {stage} job to Cloud Batch...")

    # Build job configuration
    job_config = _build_batch_job_config(
        stage=stage,
        exp_id=exp_id,
        run_id=run_id,
        task_index=task_index,
        num_tasks=num_tasks,
        image_uri=image_uri,
        bucket_name=bucket_name,
        dir_prefix=dir_prefix,
        github_forecast_repo=github_forecast_repo,
        project_id=project_id,
        cpu_milli=cpu_milli,
        memory_mib=memory_mib,
        machine_type=machine_type,
        max_run_duration=max_run_duration,
        batch_sa_email=batch_sa_email,
    )

    if handle_dry_run(
        {"dry_run": dry_run},
        f"Submit batch job {job_id}",
        {"job_config": json.dumps(job_config, indent=2)},
    ):
        return 0

    # Write config to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(job_config, f, indent=2)
        temp_file = f.name

    try:
        # Submit job
        cmd = [
            "gcloud",
            "batch",
            "jobs",
            "submit",
            job_id,
            f"--project={project_id}",
            f"--location={region}",
            f"--config={temp_file}",
        ]

        result = subprocess.run(cmd, check=False)

        if result.returncode != 0:
            error("Job submission failed")
            return 1

        success("Job submitted successfully!")
        info(f"Job Name: projects/{project_id}/locations/{region}/jobs/{job_id}")
        print()
        info("Monitor with:")
        info(f"  gcloud batch jobs describe {job_id} --location={region}")
        print()
        info("View logs:")
        info(
            f'  gcloud logging read \'resource.type="batch.googleapis.com/Job" '
            f'AND labels.job_uid="{job_id}"\' --limit=50'
        )

        if wait:
            warning("--wait not yet implemented")
            info("Use: gcloud batch jobs describe --wait")

        return 0

    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def _build_env_from_config(config: dict[str, Any]) -> dict[str, str]:
    """Build environment variables from configuration.

    Extracts all necessary configuration values and converts them to
    environment variables suitable for Docker Compose.

    Parameters
    ----------
    config : dict[str, Any]
        Configuration dict

    Returns
    -------
    dict[str, str]
        Dictionary of environment variables
    """
    google_cloud = config.get("google_cloud", {})
    github = config.get("github", {})
    storage = config.get("storage", {})
    logging_config = config.get("logging", {})

    env = {
        # Google Cloud
        "PROJECT_ID": google_cloud.get("project_id", ""),
        "REGION": google_cloud.get("region", ""),
        "BUCKET_NAME": google_cloud.get("bucket_name", ""),
        # GitHub (include PAT from secrets if present)
        "GITHUB_FORECAST_REPO": github.get("forecast_repo", ""),
        "GITHUB_MODELING_SUITE_REPO": github.get("modeling_suite_repo", ""),
        "GITHUB_MODELING_SUITE_REF": github.get("modeling_suite_ref", "main"),
        "GITHUB_PAT": github.get("personal_access_token", ""),
        # Storage
        "DIR_PREFIX": storage.get("dir_prefix", ""),
        # Logging
        "LOG_LEVEL": logging_config.get("level", "INFO"),
        "STORAGE_VERBOSE": str(logging_config.get("storage_verbose", True)).lower(),
    }

    return env


def _run_job_local(
    ctx: dict[str, Any],
    config: dict[str, Any],
    stage: str,
    exp_id: str,
    run_id: str | None,
    task_index: int,
    num_tasks: int | None,
    auto_confirm: bool,
    verbose: bool,
    dry_run: bool,
    project_directory: Path,
) -> int:
    """Run individual job locally with docker compose.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context
    config : dict[str, Any]
        Configuration dict
    stage : str
        Stage (A, B, or C)
    exp_id : str
        Experiment ID
    run_id : str | None
        Run ID
    task_index : int
        Task index for stage B
    num_tasks : int | None
        Number of tasks for stage C
    auto_confirm : bool
        Auto-confirm without prompting
    verbose : bool
        Verbose output
    dry_run : bool
        Dry run mode
    project_directory : Path
        Absolute path to Docker Compose project directory

    Returns
    -------
    int
        Exit code
    """
    # Get config values
    docker = get_docker_config(config)
    image_name = docker["image_name"]
    image_tag = docker["image_tag"]
    pipeline = config.get("pipeline", {})
    dir_prefix = pipeline.get("dir_prefix", "pipeline/flu/")

    # Auto-generate run_id for stage A if not provided
    if stage == "A" and not run_id:
        run_id = generate_run_id()

    # Build storage path
    run_id_display = run_id if run_id else "<auto-generated>"
    storage_path = f"./local/bucket/{dir_prefix}{exp_id}/{run_id_display}/"

    # Build confirmation info
    confirmation_info = {
        "command_type": "job",
        "exp_id": exp_id,
        "run_id": run_id if run_id else "<auto-generated>",
        "environment": ctx.get("environment", ""),
        "profile": ctx.get("profile", ""),
        "storage_path": storage_path,
        "stage": stage,
        "image_name": image_name,
        "image_tag": image_tag,
    }

    if stage == "B":
        confirmation_info["task_index"] = task_index
    elif stage == "C":
        confirmation_info["num_tasks"] = num_tasks

    # Show confirmation and prompt
    confirmation_message = format_confirmation(confirmation_info, mode="local")
    if not prompt_confirmation(confirmation_message, auto_confirm=auto_confirm):
        info("Operation cancelled.")
        return 0

    info(f"Running Stage {stage} locally with Docker Compose...")
    info(f"Experiment ID: {exp_id}")
    if run_id:
        info(f"Run ID: {run_id}")
    info(f"Project directory: {project_directory}")

    # Build base environment variables from config
    base_env = _build_env_from_config(config)

    # Determine service and add runtime-specific env vars
    if stage == "A":
        service = "builder"
        runtime_vars = {"EXP_ID": exp_id, "RUN_ID": run_id}
    elif stage == "B":
        service = "runner"
        runtime_vars = {
            "EXP_ID": exp_id,
            "RUN_ID": run_id,
            "TASK_INDEX": str(task_index),
        }
    else:  # C
        service = "output"
        runtime_vars = {
            "EXP_ID": exp_id,
            "RUN_ID": run_id,
            "NUM_TASKS": str(num_tasks),
        }

    # Merge base config env vars with runtime vars (runtime vars take precedence)
    env_vars = {**base_env, **runtime_vars}

    result = _run_docker_compose_stage(
        project_directory=project_directory,
        service=service,
        env_vars=env_vars,
        dry_run=dry_run,
    )

    if result == 0:
        success(f"Stage {stage} completed successfully")
        info(f"Results in: ./local/bucket/{exp_id}/{run_id}/")
    else:
        error(f"Stage {stage} failed")

    return result


def _run_docker_compose_stage(
    project_directory: Path,
    service: str,
    env_vars: dict[str, str],
    dry_run: bool,
) -> int:
    """Run a docker compose service.

    Parameters
    ----------
    project_directory : Path
        Absolute path to Docker Compose project directory
    service : str
        Service name (builder, runner, output)
    env_vars : dict[str, str]
        Environment variables
    dry_run : bool
        Dry run mode

    Returns
    -------
    int
        Exit code
    """
    # Check Docker availability
    if not dry_run and not check_docker_available():
        error("Docker is not installed or not in PATH")
        info("Install Docker Engine or OrbStack (macOS)")
        return 1

    # Use --project-directory to specify compose file location (no chdir needed)
    cmd = [
        "docker",
        "compose",
        "--project-directory",
        str(project_directory),
        "run",
        "--rm",
        service,
    ]

    if handle_dry_run(
        {"dry_run": dry_run},
        f"Run Docker Compose service '{service}'",
        {"command": " ".join(cmd), "env_vars": str(env_vars)},
    ):
        return 0

    # Set environment variables for subprocess
    env = prepare_subprocess_env(env_vars)

    # Execute command (no directory change needed)
    result = subprocess.run(cmd, env=env, check=False)
    return result.returncode


def _build_batch_job_config(
    stage: str,
    exp_id: str,
    run_id: str,
    task_index: int,
    num_tasks: int | None,
    image_uri: str,
    bucket_name: str,
    dir_prefix: str,
    github_forecast_repo: str,
    project_id: str,
    cpu_milli: int,
    memory_mib: int,
    machine_type: str,
    max_run_duration: int,
    batch_sa_email: str,
) -> dict[str, Any]:
    """Build Cloud Batch job configuration.

    Parameters
    ----------
    stage : str
        Stage (A, B, or C)
    exp_id : str
        Experiment ID
    run_id : str
        Run ID
    task_index : int
        Task index for stage B
    num_tasks : int | None
        Number of tasks for stage C
    image_uri : str
        Docker image URI
    bucket_name : str
        GCS bucket name
    dir_prefix : str
        Directory prefix
    github_forecast_repo : str
        GitHub forecast repo
    project_id : str
        Google Cloud project ID
    cpu_milli : int
        CPU in milli-cores
    memory_mib : int
        Memory in MiB
    machine_type : str
        Machine type (optional)
    max_run_duration : int
        Max run duration in seconds
    batch_sa_email : str
        Batch service account email

    Returns
    -------
    dict[str, Any]
        Job configuration dict
    """
    stage_name = {"A": "builder", "B": "runner", "C": "output"}[stage]

    # Sanitize labels for GCP compliance (exp_id may contain '/')
    exp_id_label = sanitize_label_value(exp_id)
    run_id_label = sanitize_label_value(run_id)

    # Build environment variables
    env_vars = {
        "EXECUTION_MODE": "cloud",
        "GCS_BUCKET": bucket_name,
        "DIR_PREFIX": dir_prefix,
        "EXP_ID": exp_id,
        "RUN_ID": run_id,
    }

    if stage == "A":
        env_vars["GITHUB_FORECAST_REPO"] = github_forecast_repo
        entrypoint = "/bin/bash"
        commands = ["/scripts/run_builder.sh"]
    elif stage == "B":
        env_vars["TASK_INDEX"] = str(task_index)
        entrypoint = "python3"
        commands = ["-u", "/scripts/main_runner.py"]
    else:  # C
        env_vars["NUM_TASKS"] = str(num_tasks)
        env_vars["GITHUB_FORECAST_REPO"] = github_forecast_repo
        env_vars["GCLOUD_PROJECT_ID"] = project_id
        env_vars["GITHUB_PAT_SECRET"] = "github-pat"
        env_vars["FORECAST_REPO_DIR"] = "/data/forecast/"
        entrypoint = "/bin/bash"
        commands = ["/scripts/run_output.sh"]

    # Build task spec
    task_spec = {
        "runnables": [
            {
                "container": {
                    "imageUri": image_uri,
                    "entrypoint": entrypoint,
                    "commands": commands,
                }
            }
        ],
        "environment": {"variables": env_vars},
        "computeResource": {
            "cpuMilli": cpu_milli,
            "memoryMib": memory_mib,
        },
        "maxRunDuration": f"{max_run_duration}s",
    }

    # Build allocation policy
    allocation_policy = {"serviceAccount": {"email": batch_sa_email}}

    if machine_type:
        instances = {"policy": {"machineType": machine_type}}

        # C4D machines require hyperdisk
        if machine_type.startswith("c4d-"):
            instances["installGpuDrivers"] = False
            instances["policy"]["provisioningModel"] = "STANDARD"
            instances["policy"]["bootDisk"] = {"type": "hyperdisk-balanced", "sizeGb": 50}

        allocation_policy["instances"] = [instances]

    # Build complete job config
    job_config = {
        "labels": {
            "component": "epymodelingsuite",
            "stage": stage_name,
            "exp_id": exp_id_label,
            "run_id": run_id_label,
            "managed-by": "manual",
        },
        "taskGroups": [{"taskCount": 1, "taskSpec": task_spec}],
        "logsPolicy": {"destination": "CLOUD_LOGGING"},
        "allocationPolicy": allocation_policy,
    }

    return job_config


