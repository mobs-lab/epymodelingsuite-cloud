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
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests

from epycloud.exceptions import CloudAPIError, ConfigError, ValidationError
from epycloud.lib.command_helpers import (
    get_gcloud_access_token,
    get_project_root,
    handle_dry_run,
    prepare_subprocess_env,
    require_config,
)
from epycloud.lib.output import error, info, success, warning
from epycloud.lib.validation import validate_exp_id, validate_run_id


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the run command parser.

    Args:
        subparsers: Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "run",
        help="Execute pipeline stages or workflows",
        description="""Run pipeline workflows (complete A→B→C execution) or individual stages/jobs.

Available subcommands:
  workflow    Submit complete workflow (all stages: A → B → C)
  job         Run a single stage or task (A, B, or C)

Examples:
  epycloud run workflow --exp-id my-experiment
  epycloud run job --stage A --exp-id my-experiment
  epycloud run job --stage B --exp-id my-exp --run-id <run_id> --task-index 0
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Store parser for help printing
    parser.set_defaults(_run_parser=parser)

    # Create subcommands for workflow vs job
    run_subparsers = parser.add_subparsers(dest="run_subcommand", help="Run mode")

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
        "--wait",
        action="store_true",
        help="Wait for completion and stream logs",
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


def handle(ctx: dict[str, Any]) -> int:
    """Handle the run command.

    Args:
        ctx: Command context with config and args

    Returns:
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

    Args:
        ctx: Command context

    Returns:
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
    try:
        exp_id = validate_exp_id(args.exp_id)
        run_id = validate_run_id(args.run_id) if args.run_id else None
    except ValidationError as e:
        error(str(e))
        return 1

    local = args.local
    skip_output = args.skip_output
    max_parallelism = args.max_parallelism
    wait = args.wait

    if local:
        return _run_workflow_local(
            config=config,
            exp_id=exp_id,
            run_id=run_id,
            skip_output=skip_output,
            verbose=verbose,
            dry_run=dry_run,
        )
    else:
        return _run_workflow_cloud(
            config=config,
            exp_id=exp_id,
            run_id=run_id,
            skip_output=skip_output,
            max_parallelism=max_parallelism,
            wait=wait,
            verbose=verbose,
            dry_run=dry_run,
        )


def _handle_job(ctx: dict[str, Any]) -> int:
    """Handle individual job execution.

    Args:
        ctx: Command context

    Returns:
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
    try:
        exp_id = validate_exp_id(args.exp_id)
        run_id = validate_run_id(args.run_id) if args.run_id else None
    except ValidationError as e:
        error(str(e))
        return 1

    task_index = args.task_index
    num_tasks = args.num_tasks
    local = args.local
    wait = args.wait

    # Validate requirements
    if stage in ["B", "C"] and not run_id:
        error(f"Stage {stage} requires --run-id")
        return 1

    if stage == "C" and not num_tasks:
        error("Stage C requires --num-tasks")
        return 1

    if local:
        return _run_job_local(
            config=config,
            stage=stage,
            exp_id=exp_id,
            run_id=run_id,
            task_index=task_index,
            num_tasks=num_tasks,
            verbose=verbose,
            dry_run=dry_run,
        )
    else:
        return _run_job_cloud(
            config=config,
            stage=stage,
            exp_id=exp_id,
            run_id=run_id,
            task_index=task_index,
            num_tasks=num_tasks,
            wait=wait,
            verbose=verbose,
            dry_run=dry_run,
        )


def _run_workflow_cloud(
    config: dict[str, Any],
    exp_id: str,
    run_id: str | None,
    skip_output: bool,
    max_parallelism: int | None,
    wait: bool,
    verbose: bool,
    dry_run: bool,
) -> int:
    """Submit workflow to Cloud Workflows.

    Args:
        config: Configuration dict
        exp_id: Experiment ID
        run_id: Optional run ID (auto-generated in workflow if not provided)
        skip_output: Skip stage C
        max_parallelism: Max parallel tasks
        wait: Wait for completion
        verbose: Verbose output
        dry_run: Dry run mode

    Returns:
        Exit code
    """
    info("Submitting workflow to Cloud Workflows...")
    info(f"Experiment ID: {exp_id}")

    # Get config values
    google_cloud_config = config.get("google_cloud", {})
    github_config = config.get("github", {})
    pipeline_config = config.get("pipeline", {})

    project_id = google_cloud_config.get("project_id")
    region = google_cloud_config.get("region", "us-central1")
    bucket_name = google_cloud_config.get("bucket_name")
    dir_prefix = pipeline_config.get("dir_prefix", "pipeline/flu/")
    github_forecast_repo = github_config.get("forecast_repo", "")

    if not max_parallelism:
        max_parallelism = pipeline_config.get("max_parallelism", 100)

    # Validate required config
    if not project_id:
        error("google_cloud.project_id not configured")
        return 2
    if not bucket_name:
        error("google_cloud.bucket_name not configured")
        return 2

    # Get batch service account email
    batch_sa_email = _get_batch_sa_email(project_id)

    info(f"Bucket: gs://{bucket_name}")
    info(f"Region: {region}")
    if github_forecast_repo:
        info(f"GitHub Repo: {github_forecast_repo}")
    if skip_output:
        warning("Output stage will be skipped")
    if run_id:
        info(f"Run ID: {run_id} (manually specified)")
    else:
        info("Run ID: (will be auto-generated)")

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
    config: dict[str, Any],
    exp_id: str,
    run_id: str | None,
    skip_output: bool,
    verbose: bool,
    dry_run: bool,
) -> int:
    """Run complete workflow locally with docker compose.

    Args:
        config: Configuration dict
        exp_id: Experiment ID
        run_id: Optional run ID
        skip_output: Skip stage C
        verbose: Verbose output
        dry_run: Dry run mode

    Returns:
        Exit code
    """
    info("Running workflow locally with Docker Compose...")
    info(f"Experiment ID: {exp_id}")

    # Generate run ID if not provided
    if not run_id:
        run_id = _generate_run_id()
        info(f"Generated Run ID: {run_id}")
    else:
        info(f"Run ID: {run_id}")

    project_root = get_project_root()

    # Stage A: Builder
    info("")
    info("=" * 60)
    info("Stage A: Builder (generating input files)")
    info("=" * 60)

    result = _run_docker_compose_stage(
        project_root=project_root,
        service="builder",
        env_vars={"EXP_ID": exp_id, "RUN_ID": run_id},
        dry_run=dry_run,
    )

    if result != 0:
        error("Stage A failed")
        return result

    success("Stage A completed successfully")

    # Detect number of tasks from builder artifacts
    bucket_path = project_root / "local" / "bucket" / exp_id / run_id / "builder-artifacts"

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
            project_root=project_root,
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
            project_root=project_root,
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
    config: dict[str, Any],
    stage: str,
    exp_id: str,
    run_id: str | None,
    task_index: int,
    num_tasks: int | None,
    wait: bool,
    verbose: bool,
    dry_run: bool,
) -> int:
    """Submit individual job to Cloud Batch.

    Args:
        config: Configuration dict
        stage: Stage (A, B, or C)
        exp_id: Experiment ID
        run_id: Run ID
        task_index: Task index for stage B
        num_tasks: Number of tasks for stage C
        wait: Wait for completion
        verbose: Verbose output
        dry_run: Dry run mode

    Returns:
        Exit code
    """
    info(f"Submitting Stage {stage} job to Cloud Batch...")
    info(f"Experiment ID: {exp_id}")

    if run_id:
        info(f"Run ID: {run_id}")

    if stage == "B":
        info(f"Task Index: {task_index}")
    elif stage == "C":
        info(f"Number of Tasks: {num_tasks}")

    # Get configuration
    google_cloud_config = config.get("google_cloud", {})
    docker_config = config.get("docker", {})
    github_config = config.get("github", {})
    pipeline_config = config.get("pipeline", {})
    resources_config = config.get("resources", {})

    project_id = google_cloud_config.get("project_id")
    region = google_cloud_config.get("region", "us-central1")
    bucket_name = google_cloud_config.get("bucket_name")
    dir_prefix = pipeline_config.get("dir_prefix", "pipeline/flu/")

    # Get image info
    registry = docker_config.get("registry", "us-central1-docker.pkg.dev")
    repo_name = docker_config.get("repo_name", "epymodelingsuite-repo")
    image_name = docker_config.get("image_name", "epymodelingsuite")
    image_tag = docker_config.get("image_tag", "latest")
    image_uri = f"{registry}/{project_id}/{repo_name}/{image_name}:{image_tag}"

    # Get stage-specific resources
    stage_key = f"stage_{stage.lower()}"
    stage_resources = resources_config.get(stage_key, {})
    cpu_milli = stage_resources.get("cpu_milli", 2000)
    memory_mib = stage_resources.get("memory_mib", 8192)
    machine_type = stage_resources.get("machine_type", "")
    max_run_duration = stage_resources.get("max_run_duration", 3600)

    # Validate
    if not project_id or not bucket_name:
        error("Missing required configuration: project_id or bucket_name")
        return 2

    # Get batch service account
    batch_sa_email = _get_batch_sa_email(project_id)

    # Generate job ID
    timestamp = int(time.time())
    job_id = f"epy-{timestamp}-stage-{stage.lower()}-manual"

    # Auto-generate run_id for stage A if not provided
    if stage == "A" and not run_id:
        run_id = _generate_run_id()
        info(f"Generated Run ID: {run_id}")

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
        github_forecast_repo=github_config.get("forecast_repo", ""),
        cpu_milli=cpu_milli,
        memory_mib=memory_mib,
        machine_type=machine_type,
        max_run_duration=max_run_duration,
        batch_sa_email=batch_sa_email,
    )

    info("")
    info("Configuration:")
    info(f"  Job ID: {job_id}")
    info(f"  Image: {image_uri}")
    info(f"  CPU: {cpu_milli} milli-cores")
    info(f"  Memory: {memory_mib} MiB")
    if machine_type:
        info(f"  Machine Type: {machine_type}")

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


def _run_job_local(
    config: dict[str, Any],
    stage: str,
    exp_id: str,
    run_id: str | None,
    task_index: int,
    num_tasks: int | None,
    verbose: bool,
    dry_run: bool,
) -> int:
    """Run individual job locally with docker compose.

    Args:
        config: Configuration dict
        stage: Stage (A, B, or C)
        exp_id: Experiment ID
        run_id: Run ID
        task_index: Task index for stage B
        num_tasks: Number of tasks for stage C
        verbose: Verbose output
        dry_run: Dry run mode

    Returns:
        Exit code
    """
    info(f"Running Stage {stage} locally with Docker Compose...")
    info(f"Experiment ID: {exp_id}")

    # Auto-generate run_id for stage A if not provided
    if stage == "A" and not run_id:
        run_id = _generate_run_id()
        info(f"Generated Run ID: {run_id}")
    elif run_id:
        info(f"Run ID: {run_id}")

    project_root = get_project_root()

    # Determine service and env vars
    if stage == "A":
        service = "builder"
        env_vars = {"EXP_ID": exp_id, "RUN_ID": run_id}
    elif stage == "B":
        service = "runner"
        env_vars = {
            "EXP_ID": exp_id,
            "RUN_ID": run_id,
            "TASK_INDEX": str(task_index),
        }
        info(f"Task Index: {task_index}")
    else:  # C
        service = "output"
        env_vars = {
            "EXP_ID": exp_id,
            "RUN_ID": run_id,
            "NUM_TASKS": str(num_tasks),
        }
        info(f"Number of Tasks: {num_tasks}")

    result = _run_docker_compose_stage(
        project_root=project_root,
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
    project_root: Path,
    service: str,
    env_vars: dict[str, str],
    dry_run: bool,
) -> int:
    """Run a docker compose service.

    Args:
        project_root: Project root directory
        service: Service name (builder, runner, output)
        env_vars: Environment variables
        dry_run: Dry run mode

    Returns:
        Exit code
    """
    cmd = ["docker", "compose", "run", "--rm", service]

    if handle_dry_run(
        {"dry_run": dry_run},
        f"Run Docker Compose service '{service}'",
        {"command": " ".join(cmd), "env_vars": str(env_vars)},
    ):
        return 0

    # Set environment variables for subprocess
    env = prepare_subprocess_env(env_vars)

    # Change to project root
    original_dir = Path.cwd()
    try:
        os.chdir(project_root)
        result = subprocess.run(cmd, env=env, check=False)
        return result.returncode
    finally:
        os.chdir(original_dir)


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
    cpu_milli: int,
    memory_mib: int,
    machine_type: str,
    max_run_duration: int,
    batch_sa_email: str,
) -> dict[str, Any]:
    """Build Cloud Batch job configuration.

    Args:
        stage: Stage (A, B, or C)
        exp_id: Experiment ID
        run_id: Run ID
        task_index: Task index for stage B
        num_tasks: Number of tasks for stage C
        image_uri: Docker image URI
        bucket_name: GCS bucket name
        dir_prefix: Directory prefix
        github_forecast_repo: GitHub forecast repo
        cpu_milli: CPU in milli-cores
        memory_mib: Memory in MiB
        machine_type: Machine type (optional)
        max_run_duration: Max run duration in seconds
        batch_sa_email: Batch service account email

    Returns:
        Job configuration dict
    """
    stage_name = {"A": "builder", "B": "runner", "C": "output"}[stage]

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
        entrypoint = "python3"
        commands = ["-u", "/scripts/main_output.py"]

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
            "exp_id": exp_id,
            "run_id": run_id,
            "managed-by": "manual",
        },
        "taskGroups": [{"taskCount": 1, "taskSpec": task_spec}],
        "logsPolicy": {"destination": "CLOUD_LOGGING"},
        "allocationPolicy": allocation_policy,
    }

    return job_config


def _get_batch_sa_email(project_id: str) -> str:
    """Get batch service account email.

    Args:
        project_id: GCP project ID

    Returns:
        Service account email
    """
    # Try to get from Terraform output
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", "batch_runtime_sa_email"],
            cwd="terraform",
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Fall back to default
    return f"batch-runtime@{project_id}.iam.gserviceaccount.com"


def _generate_run_id() -> str:
    """Generate a unique run ID.

    Returns:
        Run ID in format: YYYYMMDD-HHMMSS-<uuid-prefix>
    """
    now = datetime.now()
    date_part = now.strftime("%Y%m%d")
    time_part = now.strftime("%H%M%S")
    unique_id = str(uuid4())[:8]
    return f"{date_part}-{time_part}-{unique_id}"
