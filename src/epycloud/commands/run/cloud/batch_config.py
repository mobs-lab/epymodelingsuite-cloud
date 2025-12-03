"""Cloud Batch job configuration builder."""

from typing import Any

from epycloud.lib.validation import sanitize_label_value


def build_batch_job_config(
    stage: str,
    exp_id: str,
    run_id: str,
    task_index: int,
    num_tasks: int | None,
    output_config: str | None,
    image_uri: str,
    bucket_name: str,
    dir_prefix: str,
    github_forecast_repo: str,
    project_id: str,
    cpu_milli: int,
    memory_mib: int,
    machine_type: str,
    max_run_duration: int,
    task_count_per_node: int,
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
    output_config : str | None
        Output config filename for Stage C (e.g., "output_projection.yaml")
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
    task_count_per_node : int
        Max tasks per VM node (1 = dedicated VM per task)
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
        env_vars["OUTPUT_CONFIG_FILE"] = output_config or ""
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
        "taskGroups": [
            {"taskCount": 1, "taskSpec": task_spec, "taskCountPerNode": task_count_per_node}
        ],
        "logsPolicy": {"destination": "CLOUD_LOGGING"},
        "allocationPolicy": allocation_policy,
    }

    return job_config
