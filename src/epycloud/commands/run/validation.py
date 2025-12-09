"""Validation and confirmation utilities for run command."""

from typing import Any

from epycloud.lib.output import error, info, success
from epycloud.lib.validation import get_machine_type_specs, validate_machine_type
from epycloud.exceptions import ValidationError
from epycloud.utils.confirmation import format_confirmation, prompt_confirmation


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


def prompt_user_confirmation(auto_confirm: bool, confirmation_info: dict[str, Any], mode: str) -> bool:
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
    info(f"Validating {stage_name} machine type '{machine_type}'...")
    try:
        validate_machine_type(machine_type, project_id, region)
        success(f"{stage_name} machine type '{machine_type}' is valid")
        info(f"Querying machine type specs...")
        cpu_milli, memory_mib = get_machine_type_specs(machine_type, project_id, region)
        info(f"{stage_name}: CPU={cpu_milli} milliCPU, Memory={memory_mib} MiB")
        return cpu_milli, memory_mib
    except ValidationError as e:
        error(str(e))
        return None
