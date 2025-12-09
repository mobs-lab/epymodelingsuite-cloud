"""Cloud workflow execution for run command."""

import json
import sys
from typing import Any

import requests

from epycloud.exceptions import CloudAPIError
from epycloud.lib.command_helpers import (
    get_batch_config,
    get_batch_service_account,
    get_gcloud_access_token,
    get_github_config,
    get_image_uri,
    handle_dry_run,
)
from epycloud.lib.output import error, info, success, warning

from ..validation import (
    build_base_confirmation_info,
    prompt_user_confirmation,
    validate_and_get_machine_specs,
)


def run_workflow_cloud(
    ctx: dict[str, Any],
    config: dict[str, Any],
    exp_id: str,
    run_id: str | None,
    skip_output: bool,
    output_config: str | None,
    max_parallelism: int | None,
    task_count_per_node: int | None,
    stage_a_machine_type_override: str | None,
    stage_b_machine_type_override: str | None,
    stage_c_machine_type_override: str | None,
    forecast_repo_ref_override: str | None,
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
    output_config : str | None
        Output config filename for Stage C (e.g., "output_projection.yaml")
    max_parallelism : int | None
        Max parallel tasks
    task_count_per_node : int | None
        Max tasks per VM node (1 = dedicated VM per task)
    stage_a_machine_type_override : str | None
        Override Stage A machine type (auto-sets CPU/memory to machine max)
    stage_b_machine_type_override : str | None
        Override Stage B machine type (auto-sets CPU/memory to machine max)
    stage_c_machine_type_override : str | None
        Override Stage C machine type (auto-sets CPU/memory to machine max)
    forecast_repo_ref_override : str | None
        Override forecast repo branch/tag/commit
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
    github_forecast_repo_ref = github["forecast_repo_ref"]
    batch_config = get_batch_config(config)

    # Apply forecast repo ref override
    if forecast_repo_ref_override:
        github_forecast_repo_ref = forecast_repo_ref_override

    if not max_parallelism:
        max_parallelism = pipeline.get("max_parallelism", 100)

    if not task_count_per_node:
        task_count_per_node = batch_config.get("task_count_per_node", 1)

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

    # Process machine type overrides for all stages
    # Stage A
    stage_a_config = batch_config.get("stage_a", {})
    stage_a_machine_type = stage_a_machine_type_override or stage_a_config.get("machine_type", "")
    stage_a_cpu_milli = stage_a_config.get("cpu_milli", 2000)
    stage_a_memory_mib = stage_a_config.get("memory_mib", 8192)

    if stage_a_machine_type_override:
        result = validate_and_get_machine_specs(
            stage_a_machine_type_override, "Stage A", project_id, region
        )
        if result is None:
            return 1
        stage_a_cpu_milli, stage_a_memory_mib = result

    # Stage B
    stage_b_config = batch_config.get("stage_b", {})
    stage_b_machine_type = stage_b_machine_type_override or stage_b_config.get("machine_type", "")
    stage_b_cpu_milli = stage_b_config.get("cpu_milli", 2000)
    stage_b_memory_mib = stage_b_config.get("memory_mib", 8192)

    if stage_b_machine_type_override:
        result = validate_and_get_machine_specs(
            stage_b_machine_type_override, "Stage B", project_id, region
        )
        if result is None:
            return 1
        stage_b_cpu_milli, stage_b_memory_mib = result

    # Stage C
    stage_c_config = batch_config.get("stage_c", {})
    stage_c_machine_type = stage_c_machine_type_override or stage_c_config.get("machine_type", "")
    stage_c_cpu_milli = stage_c_config.get("cpu_milli", 2000)
    stage_c_memory_mib = stage_c_config.get("memory_mib", 8192)

    if stage_c_machine_type_override:
        result = validate_and_get_machine_specs(
            stage_c_machine_type_override, "Stage C", project_id, region
        )
        if result is None:
            return 1
        stage_c_cpu_milli, stage_c_memory_mib = result

    # Build storage path
    generated_run_id = run_id if run_id else "<auto-generated>"
    storage_path = f"gs://{bucket_name}/{dir_prefix}{exp_id}/{generated_run_id}/"

    # Build confirmation info
    confirmation_info = build_base_confirmation_info(ctx, "workflow", exp_id, generated_run_id)
    confirmation_info.update(
        {
            "project_id": project_id,
            "region": region,
            "bucket_name": bucket_name,
            "storage_path": storage_path,
            "modeling_suite_repo": github["modeling_suite_repo"],
            "modeling_suite_ref": github["modeling_suite_ref"],
            "forecast_repo": github_forecast_repo,
            "forecast_repo_ref": github_forecast_repo_ref,
            "pat_configured": bool(github["personal_access_token"]),
            "max_parallelism": max_parallelism,
            "stage_a_machine_type": stage_a_machine_type,
            "stage_a_machine_type_override": stage_a_machine_type_override,
            "stage_b_machine_type": stage_b_machine_type,
            "stage_b_machine_type_override": stage_b_machine_type_override,
            "stage_c_machine_type": stage_c_machine_type,
            "stage_c_machine_type_override": stage_c_machine_type_override,
            "skip_output": skip_output,
            "output_config": output_config,
            "image_uri": image_uri,
        }
    )

    # Show confirmation and prompt
    if not prompt_user_confirmation(auto_confirm, confirmation_info, mode="cloud"):
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

    if task_count_per_node:
        workflow_arg["taskCountPerNode"] = task_count_per_node

    if stage_a_machine_type_override:
        workflow_arg["stageAMachineType"] = stage_a_machine_type_override
        workflow_arg["stageACpuMilli"] = stage_a_cpu_milli
        workflow_arg["stageAMemoryMib"] = stage_a_memory_mib

    if stage_b_machine_type_override:
        workflow_arg["stageBMachineType"] = stage_b_machine_type_override
        workflow_arg["stageBCpuMilli"] = stage_b_cpu_milli
        workflow_arg["stageBMemoryMib"] = stage_b_memory_mib

    if stage_c_machine_type_override:
        workflow_arg["stageCMachineType"] = stage_c_machine_type_override
        workflow_arg["stageCCpuMilli"] = stage_c_cpu_milli
        workflow_arg["stageCMemoryMib"] = stage_c_memory_mib

    if github_forecast_repo_ref:
        workflow_arg["forecastRepoRef"] = github_forecast_repo_ref

    if skip_output:
        workflow_arg["runOutputStage"] = False

    if output_config:
        workflow_arg["outputConfigFile"] = output_config

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
