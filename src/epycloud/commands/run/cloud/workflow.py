"""Cloud workflow execution for run command."""

import sys
from typing import Any

import requests

from epycloud.exceptions import CloudAPIError
from epycloud.execution import (
    ExecutionAuthenticationError,
    ExecutionBackend,
    PipelineRunSpec,
    StageResources,
)
from epycloud.lib.command_helpers import (
    DEFAULT_WORKFLOW_NAME,
    get_batch_config,
    get_batch_service_account,
    get_github_config,
    get_image_uri,
    get_workflow_name,
    handle_dry_run,
)
from epycloud.lib.output import error, info, status, success, warning

from ..validation import (
    build_base_confirmation_info,
    prompt_user_confirmation,
    resolve_stage_candidates,
    validate_cross_region_preflight,
)


def run_workflow_gcp(
    backend: ExecutionBackend,
    ctx: dict[str, Any],
    config: dict[str, Any],
    exp_id: str,
    run_id: str | None,
    skip_output: bool,
    output_config: str | None,
    max_parallelism: int | None,
    batch_region_override: str | None,
    task_count_per_node: int | None,
    stage_a_machine_type_override: str | None,
    stage_b_machine_type_override: str | None,
    stage_c_machine_type_override: str | None,
    forecast_repo_ref_override: str | None,
    billing_project_override: str | None,
    wait: bool,
    auto_confirm: bool,
    verbose: bool,
    dry_run: bool,
) -> int:
    """Prepare and submit a workflow through the GCP backend.

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
    batch_region_override : str | None
        Override the Cloud Batch data-plane region
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
    billing_project_override : str | None
        Override billing project label
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
    compute_region = batch_region_override or region
    configured_regions = google_cloud.get("batch_regions")
    if configured_regions is None:
        configured_region_names = {region}
    elif isinstance(configured_regions, dict):
        configured_region_names = set(configured_regions)
    else:
        error("google_cloud.batch_regions must be a mapping")
        return 2
    if compute_region not in configured_region_names:
        allowed = ", ".join(sorted(configured_region_names))
        error(f"Batch region '{compute_region}' is not configured. Configured regions: {allowed}")
        return 2
    bucket_name = google_cloud.get("bucket_name")
    workflow_name = get_workflow_name(config)
    storage = config.get("storage", {})
    dir_prefix = storage.get("dir_prefix", "pipeline/flu/")
    if dir_prefix and not dir_prefix.endswith("/"):
        dir_prefix += "/"
    github = get_github_config(config)
    github_forecast_repo = github["forecast_repo"]
    github_forecast_repo_ref = github["forecast_repo_ref"]
    batch_config = get_batch_config(config)

    # Apply forecast repo ref override
    if forecast_repo_ref_override:
        github_forecast_repo_ref = forecast_repo_ref_override

    if not max_parallelism:
        max_parallelism = batch_config.get("max_parallelism", 100)

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
    image_uri = (
        get_image_uri(config)
        if compute_region == region
        else get_image_uri(config, region=compute_region)
    )

    # Extract image tag from config for runtime override
    docker_config = config.get("docker", {})
    image_tag = docker_config.get("image_tag", "latest")

    stage_configs = {stage: batch_config.get(f"stage_{stage}", {}) for stage in ("a", "b", "c")}
    stage_defaults = {
        "a": (2000, 7168, 3600),
        "b": (2000, 7168, 36000),
        "c": (4000, 15360, 7200),
    }
    stage_overrides = {
        "a": stage_a_machine_type_override,
        "b": stage_b_machine_type_override,
        "c": stage_c_machine_type_override,
    }
    stage_candidates: dict[str, tuple[StageResources, ...]] = {}
    stage_pinned: dict[str, bool] = {}
    for stage in ("a", "b", "c"):
        default_cpu, default_memory, default_duration = stage_defaults[stage]
        resolved = resolve_stage_candidates(
            stage_configs[stage],
            stage_overrides[stage],
            f"Stage {stage.upper()}",
            project_id,
            compute_region,
            default_cpu_milli=default_cpu,
            default_memory_mib=default_memory,
            default_max_run_duration=default_duration,
        )
        if resolved is None:
            return 1
        stage_candidates[stage], stage_pinned[stage] = resolved

    stage_resources = {stage: candidates[0] for stage, candidates in stage_candidates.items()}

    if not validate_cross_region_preflight(
        config,
        project_id,
        region,
        compute_region,
        image_tag,
        verbose,
    ):
        return 1

    # Extract labels
    profile_meta = config.get("_meta", {}).get("profile") or {}
    profile_name = profile_meta.get("name", "") if isinstance(profile_meta, dict) else ""
    billing_project = google_cloud.get("billing_project", "")

    # Apply billing project override
    if billing_project_override is not None:
        billing_project = billing_project_override

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
            "task_count_per_node": task_count_per_node,
            "stage_a_machine_type": stage_resources["a"].machine_type,
            "stage_a_machine_type_override": stage_a_machine_type_override,
            "stage_a_machine_types": [item.machine_type for item in stage_candidates["a"]],
            "stage_a_pinned": stage_pinned["a"],
            "stage_a_cpu_milli": stage_resources["a"].cpu_milli,
            "stage_a_memory_mib": stage_resources["a"].memory_mib,
            "stage_a_max_run_duration": stage_resources["a"].max_run_duration,
            "stage_b_machine_type": stage_resources["b"].machine_type,
            "stage_b_machine_type_override": stage_b_machine_type_override,
            "stage_b_machine_types": [item.machine_type for item in stage_candidates["b"]],
            "stage_b_pinned": stage_pinned["b"],
            "stage_b_cpu_milli": stage_resources["b"].cpu_milli,
            "stage_b_memory_mib": stage_resources["b"].memory_mib,
            "stage_b_max_run_duration": stage_resources["b"].max_run_duration,
            "stage_c_machine_type": stage_resources["c"].machine_type,
            "stage_c_machine_type_override": stage_c_machine_type_override,
            "stage_c_machine_types": [item.machine_type for item in stage_candidates["c"]],
            "stage_c_pinned": stage_pinned["c"],
            "stage_c_cpu_milli": stage_resources["c"].cpu_milli,
            "stage_c_memory_mib": stage_resources["c"].memory_mib,
            "stage_c_max_run_duration": stage_resources["c"].max_run_duration,
            "skip_output": skip_output,
            "output_config": output_config,
            "image_uri": image_uri,
            "image_tag": image_tag,
        }
    )
    if billing_project:
        confirmation_info["billing_project"] = billing_project
    if compute_region != region:
        confirmation_info["batch_region"] = compute_region
    # Surfaced only when submitting to a non-default pipeline, so default runs
    # keep their existing confirmation output verbatim.
    if workflow_name != DEFAULT_WORKFLOW_NAME:
        confirmation_info["workflow_name"] = workflow_name

    # Show confirmation and prompt
    if not prompt_user_confirmation(auto_confirm, confirmation_info, mode="cloud"):
        return 0

    status("Submitting workflow to Cloud Workflows...")

    plan = backend.plan_pipeline(
        PipelineRunSpec(
            experiment_id=exp_id,
            run_id=run_id,
            storage_bucket=bucket_name,
            storage_prefix=dir_prefix,
            forecast_repo=github_forecast_repo,
            forecast_repo_ref=github_forecast_repo_ref,
            image_tag=image_tag,
            execution_identity=batch_sa_email,
            max_parallelism=max_parallelism,
            task_count_per_node=task_count_per_node,
            stage_resources=stage_resources,
            compute_region=compute_region,
            stage_candidates=stage_candidates,
            stage_pinned=stage_pinned,
            profile=profile_name,
            billing_project=billing_project,
            skip_output=skip_output,
            output_config=output_config,
        )
    )

    if handle_dry_run(
        {"dry_run": dry_run},
        "Submit workflow",
        plan.display_details,
    ):
        return 0

    # Submit workflow
    try:
        run_ref = backend.submit_pipeline(plan)
        execution_name = run_ref.resource_name

        success("Workflow submitted successfully!")
        info(f"Execution: {execution_name}")
        print()

        # Extract execution ID from name
        execution_id = run_ref.run_id

        if execution_id:
            info("Monitor with:")
            info(
                f"  gcloud workflows executions describe {execution_id} "
                f"--workflow={workflow_name} --location={region}"
            )
            info(f"  gcloud workflows executions list {workflow_name} --location={region}")
            print()
            info("Or use:")
            info(f"  epycloud workflow describe {execution_id}")
            info(f"  epycloud workflow logs {execution_id} --follow")

        if wait:
            warning("--wait not yet implemented for workflows")
            info("Use: gcloud workflows executions describe --wait")

        return 0

    except (CloudAPIError, ExecutionAuthenticationError) as e:
        error(str(e))
        return 1
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
