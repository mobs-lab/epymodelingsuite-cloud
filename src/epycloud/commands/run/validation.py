"""Validation and confirmation utilities for run command."""

import subprocess
import sys
from typing import Any

from epycloud.commands.build import cloud as build_cloud
from epycloud.exceptions import ValidationError
from epycloud.execution import StageResources
from epycloud.execution.gcp_machines import validate_hyperdisk_family
from epycloud.lib.command_helpers import get_image_uri
from epycloud.lib.output import error, info, status, success, warning
from epycloud.lib.validation import get_machine_type_specs, validate_machine_type
from epycloud.utils.confirmation import format_confirmation, prompt_confirmation


def validate_cross_region_preflight(
    config: dict[str, Any],
    project_id: str,
    source_region: str,
    compute_region: str,
    image_tag: str,
    verbose: bool,
) -> bool:
    """Verify the image replica and subnet needed by a cross-region run."""
    if compute_region == source_region:
        return True

    source_image = get_image_uri(config, tag=image_tag, region=source_region)
    destination_image = get_image_uri(config, tag=image_tag, region=compute_region)
    status(f"Checking image replica in {compute_region}...")
    source_digest = build_cloud.resolve_image_digest(
        project_id=project_id,
        image_uri=source_image,
        verbose=verbose,
    )
    destination_digest = build_cloud.resolve_image_digest(
        project_id=project_id,
        image_uri=destination_image,
        verbose=verbose,
    )
    if source_digest is None or destination_digest != source_digest:
        error(f"Image tag '{image_tag}' is not an identical replica in {compute_region}.")
        info("Replicate it with:")
        info(
            "  uv run epycloud build replicate "
            f"--from {source_region} --to {compute_region} --tag {image_tag}"
        )
        return False

    subnet_base_name = config.get("google_cloud", {}).get(
        "subnet_name", "epymodelingsuite-subnet"
    )
    subnet_name = f"{subnet_base_name}-{compute_region}"
    status(f"Checking Batch subnet '{subnet_name}'...")
    try:
        result = subprocess.run(
            [
                "gcloud",
                "compute",
                "networks",
                "subnets",
                "describe",
                subnet_name,
                f"--project={project_id}",
                f"--region={compute_region}",
                "--format=value(selfLink)",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        error(f"Unable to verify Batch subnet in {compute_region}: {exc}")
        return False

    if result.returncode != 0 or not result.stdout.strip():
        error(f"Batch subnet '{subnet_name}' was not found in {compute_region}")
        if verbose and result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        return False

    success(f"Cross-region preflight passed for image and subnet in {compute_region}")
    return True


def build_base_confirmation_info(
    ctx: dict[str, Any],
    command_type: str,
    exp_id: str,
    run_id: str,
) -> dict[str, Any]:
    """Build base confirmation info dict with common fields.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context
    command_type : str
        Command type ('workflow' or 'job')
    exp_id : str
        Experiment ID
    run_id : str
        Run ID

    Returns
    -------
    dict[str, Any]
        Base confirmation info dict
    """
    return {
        "command_type": command_type,
        "exp_id": exp_id,
        "run_id": run_id,
        "environment": ctx.get("environment", ""),
        "profile": ctx.get("profile", ""),
    }


def add_stage_specific_info(
    confirmation_info: dict[str, Any],
    stage: str,
    task_index: int | None = None,
    num_tasks: int | None = None,
    output_config: str | None = None,
) -> None:
    """Add stage-specific information to confirmation_info dict.

    Parameters
    ----------
    confirmation_info : dict[str, Any]
        Confirmation info dict to update (modified in-place)
    stage : str
        Stage (A, B, or C)
    task_index : int | None
        Task index for stage B
    num_tasks : int | None
        Number of tasks for stage C
    output_config : str | None
        Output config filename for Stage C
    """
    if stage == "B":
        confirmation_info["task_index"] = task_index
    elif stage == "C":
        confirmation_info["num_tasks"] = num_tasks
        confirmation_info["output_config"] = output_config


def prompt_user_confirmation(
    auto_confirm: bool, confirmation_info: dict[str, Any], mode: str
) -> bool:
    """Prompt user for confirmation and handle response.

    Parameters
    ----------
    auto_confirm : bool
        Auto-confirm without prompting
    confirmation_info : dict[str, Any]
        Confirmation info dictionary
    mode : str
        Execution mode ('cloud' or 'local')

    Returns
    -------
    bool
        True if user confirmed, False otherwise
    """
    confirmation_message = format_confirmation(confirmation_info, mode=mode)
    if not prompt_confirmation(confirmation_message, auto_confirm=auto_confirm):
        info("Operation cancelled.")
        return False
    return True


def validate_and_get_machine_specs(
    machine_type: str,
    stage_name: str,
    project_id: str,
    region: str,
) -> tuple[int, int] | None:
    """Validate machine type and get CPU/memory specs.

    Parameters
    ----------
    machine_type : str
        Machine type to validate
    stage_name : str
        Stage name for display (e.g., "Stage A")
    project_id : str
        Google Cloud project ID
    region : str
        Google Cloud region

    Returns
    -------
    tuple[int, int] | None
        (cpu_milli, memory_mib) if valid, None if invalid
    """
    status(f"Validating {stage_name} machine type '{machine_type}'...")
    try:
        # Cheap local check first, so a wrong family is rejected without a
        # gcloud round-trip, and before validate_machine_type rejects "".
        validate_hyperdisk_family(machine_type, stage_name)
        validate_machine_type(machine_type, project_id, region)
        success(f"{stage_name} machine type '{machine_type}' is valid")
        status("Querying machine type specs...")
        cpu_milli, memory_mib = get_machine_type_specs(machine_type, project_id, region)
        status(f"{stage_name}: CPU={cpu_milli} milliCPU, Memory={memory_mib} MiB")
        return cpu_milli, memory_mib
    except ValidationError as e:
        error(str(e))
        return None


# Memory left for the OS and container runtime when several tasks share a VM.
# ponytail: fixed reserve matching the existing configs (e.g. 31744 = 32768 - 1024);
# measure Batch's actual overhead if packed tasks hit OOM.
RESERVED_MEMORY_MIB = 1024


def resolve_stage_candidates(
    stage_config: dict[str, Any],
    override: str | None,
    stage_name: str,
    project_id: str,
    region: str,
    *,
    default_cpu_milli: int,
    default_memory_mib: int,
    default_max_run_duration: int,
    max_task_count_per_node: int | None = None,
) -> tuple[tuple[StageResources, ...], bool] | None:
    """Resolve and validate one stage's ordered machine candidates.

    A CLI override is an explicit pin. Configured ``machine_types`` form an
    ordered fallback chain, while the legacy singular key remains a one-attempt
    compatibility path.

    ``cpu_milli`` and ``memory_mib`` are per-task requests. Each candidate keeps
    that request and gets the number of tasks that fit on its machine, capped by
    ``max_task_count_per_node`` when given.
    """
    if not isinstance(stage_config, dict):
        error(f"{stage_name} configuration must be a mapping")
        return None

    task_cpu_milli = stage_config.get("cpu_milli", default_cpu_milli)
    task_memory_mib = stage_config.get("memory_mib", default_memory_mib)
    max_run_duration = stage_config.get("max_run_duration", default_max_run_duration)

    for field, value in (
        ("cpu_milli", task_cpu_milli),
        ("memory_mib", task_memory_mib),
        ("max_run_duration", max_run_duration),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            error(f"{stage_name} {field} must be a positive integer")
            return None

    pinned = override is not None
    if override is not None:
        if not override.strip():
            error(f"{stage_name} machine type override must not be empty")
            return None
        configured = [override.strip()]
    elif "machine_types" in stage_config:
        raw_candidates = stage_config["machine_types"]
        if not isinstance(raw_candidates, list) or not raw_candidates:
            error(f"{stage_name} machine_types must be a non-empty list of strings")
            return None
        if any(not isinstance(item, str) or not item.strip() for item in raw_candidates):
            error(f"{stage_name} machine_types must contain only non-empty strings")
            return None
        configured = [item.strip() for item in raw_candidates]
        if len(configured) != len(set(configured)):
            error(f"{stage_name} machine_types must not contain duplicates")
            return None
        if "machine_type" in stage_config:
            warning(
                f"{stage_name} machine_types takes precedence over the legacy machine_type value"
            )
    else:
        legacy = stage_config.get("machine_type", "")
        if not isinstance(legacy, str):
            error(f"{stage_name} machine_type must be a string")
            return None
        configured = [legacy.strip()]

    resources: list[StageResources] = []
    for machine_type in configured:
        if not machine_type:
            # Google picks the machine, so its capacity is unknown: one task per VM.
            resources.append(
                StageResources(
                    machine_type="",
                    cpu_milli=task_cpu_milli,
                    memory_mib=task_memory_mib,
                    max_run_duration=max_run_duration,
                )
            )
            continue

        specs = validate_and_get_machine_specs(machine_type, stage_name, project_id, region)
        if specs is None:
            return None
        cpu_milli, memory_mib = specs
        if cpu_milli < task_cpu_milli:
            error(
                f"{stage_name} candidate '{machine_type}' has {cpu_milli} mCPU, "
                f"below the {task_cpu_milli} mCPU per-task request"
            )
            return None
        if memory_mib < task_memory_mib:
            error(
                f"{stage_name} candidate '{machine_type}' has {memory_mib} MiB, "
                f"below the {task_memory_mib} MiB per-task request"
            )
            return None
        # One task may use the whole VM; extra tasks must fit beside the OS reserve.
        fits = min(
            cpu_milli // task_cpu_milli,
            max(1, (memory_mib - RESERVED_MEMORY_MIB) // task_memory_mib),
        )
        if max_task_count_per_node:
            fits = min(fits, max_task_count_per_node)
        resources.append(
            StageResources(
                machine_type=machine_type,
                cpu_milli=task_cpu_milli,
                memory_mib=task_memory_mib,
                max_run_duration=max_run_duration,
                task_count_per_node=fits,
            )
        )

    return tuple(resources), pinned


def validate_stage_machine_family(machine_type: str, stage_name: str) -> bool:
    """Check a resolved machine type against the Hyperdisk boot-disk constraint.

    Unlike :func:`validate_and_get_machine_specs`, this runs on the value the
    stage will actually use (CLI override or config), so a bad machine type in
    config is caught at submission instead of at VM creation ~1080s later.

    Parameters
    ----------
    machine_type : str
        Resolved machine type. An empty string means auto-select and passes.
    stage_name : str
        Stage name for the error message (e.g. "Stage B")

    Returns
    -------
    bool
        True if usable, False if rejected (the error is already reported)
    """
    try:
        validate_hyperdisk_family(machine_type, stage_name)
        return True
    except ValidationError as e:
        error(str(e))
        return False
