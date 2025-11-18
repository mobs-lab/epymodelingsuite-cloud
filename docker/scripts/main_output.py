#!/usr/bin/env python3
"""
Stage C: Generate output files from runner results.
Loads all result pickle files from Stage B, generates formatted outputs using
dispatch_output_generator, and saves CSV.gz files to storage.
"""

import logging
import os
import sys
from pathlib import Path

import dill

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from epymodelingsuite.dispatcher import dispatch_output_generator
from epymodelingsuite.telemetry import ExecutionTelemetry, create_workflow_telemetry
from util import storage
from util.config import resolve_configs
from util.error_handling import handle_stage_error
from util.logger import setup_logger

# Task index formatting (supports up to 99999 tasks)
INDEX_WIDTH = 5


def detect_result_type(result) -> str:
    """Detect whether a result is a simulation or calibration.

    Parameters
    ----------
    result
        Result object from Stage B

    Returns
    -------
    str
        "simulation" or "calibration"

    Raises
    ------
    ValueError
        If result type cannot be determined
    """
    type_name = type(result).__name__
    if "Simulation" in type_name:
        return "simulation"
    elif "Calibration" in type_name:
        return "calibration"
    else:
        raise ValueError(f"Unknown result type: {type_name}")


def load_all_results(num_tasks: int, logger: logging.Logger) -> tuple[list, str]:
    """Load all result pickle files from Stage B.

    Parameters
    ----------
    num_tasks : int
        Number of result files to load
    logger : logging.Logger
        Logger instance for output

    Returns
    -------
    tuple[list, str]
        Tuple of (results_list, result_type) where result_type is 'simulation' or 'calibration'

    Raises
    ------
    ValueError
        If any result files are missing or if no results could be loaded
    """
    results = []
    result_type = None
    missing_tasks = []
    failed_tasks = []

    logger.info(f"Loading {num_tasks} result files from Stage B")

    # First pass: Check which files exist and load them
    for i in range(num_tasks):
        result_path = storage.get_path("runner-artifacts", f"result_{i:0{INDEX_WIDTH}d}.pkl.gz")
        logger.debug(f"Checking: {result_path}")

        try:
            raw_data = storage.load_bytes(result_path)
            result = dill.loads(raw_data)
            results.append(result)

            # Determine result type from first result
            if result_type is None:
                result_type = detect_result_type(result)
                logger.info(f"Detected result type: {result_type}")

            logger.debug(f"Loaded: {len(raw_data):,} bytes")
        except FileNotFoundError:
            logger.warning(f"MISSING: File not found: {result_path}")
            missing_tasks.append(i)
        except Exception as e:
            logger.warning(f"FAILED: {type(e).__name__}: {e}")
            failed_tasks.append(i)

    # Report results
    successful = len(results)
    total_failed = len(missing_tasks) + len(failed_tasks)

    logger.info(
        "Load summary",
        extra={
            "successful": successful,
            "total_tasks": num_tasks,
            "missing": len(missing_tasks),
            "failed": len(failed_tasks),
        },
    )

    # If any tasks failed, raise detailed error
    if total_failed > 0:
        error_msg = f"Cannot generate outputs: {total_failed} task(s) failed out of {num_tasks}\n"
        error_msg += f"Successfully completed: {successful}/{num_tasks}\n"

        if missing_tasks:
            error_msg += f"Missing result files (tasks): {missing_tasks}\n"
        if failed_tasks:
            error_msg += f"Failed to load (tasks): {failed_tasks}\n"

        error_msg += "\nPlease investigate Stage B failures before generating outputs."
        error_msg += "\nCheck logs for tasks that failed or did not complete."

        raise ValueError(error_msg)

    if successful == 0:
        raise ValueError("No results loaded - all tasks failed or no tasks were run")

    logger.info(f"Successfully loaded {len(results)} {result_type} results")
    return results, result_type


def load_configuration(config: dict, logger: logging.Logger):
    """Load and validate output configuration for the experiment.

    Parameters
    ----------
    config : dict
        Storage configuration containing exp_id and other settings
    logger : logging.Logger
        Logger instance for output

    Returns
    -------
    object
        Loaded and validated output configuration object

    Raises
    ------
    SystemExit
        If output config file is not found
    Exception
        If config file cannot be loaded or validated
    """
    # Resolve config files for this experiment
    logger.info(f"Resolving config files for exp_id: {config['exp_id']}")
    config_files = resolve_configs(config["exp_id"])

    # Load output configuration
    output_config_path = config_files["output"]

    if not output_config_path:
        exp_config_dir = Path("/data/forecast/experiments") / config["exp_id"] / "config"
        logger.error("No output config found")
        logger.error(f"Searched in: {exp_config_dir}")
        logger.error("Looking for YAML files with 'outputs' key")
        logger.error(
            "Please add output.yaml with 'outputs' key to your experiment config directory"
        )
        sys.exit(1)

    logger.debug(f"Output config: {output_config_path}")
    from epymodelingsuite.config_loader import load_output_config_from_file

    output_config = load_output_config_from_file(output_config_path)
    logger.info("Output config loaded successfully")
    return output_config


def generate_outputs(
    results: list, result_type: str, output_config, logger: logging.Logger
) -> dict:
    """Generate output files using the dispatcher.

    Parameters
    ----------
    results : list
        List of result objects from Stage B
    result_type : str
        Type of results ('simulation' or 'calibration')
    output_config : object
        Output configuration object
    logger : logging.Logger
        Logger instance for output

    Returns
    -------
    dict
        Dictionary mapping output keys to lists of OutputObject instances

    Raises
    ------
    ValueError
        If result_type is unknown or if output generation fails
    """
    logger.info(f"Generating outputs for {result_type}")

    # Prepare kwargs for dispatcher based on result type
    # Note: Registry expects plural form (simulations/calibrations)
    if result_type == "simulation":
        dispatch_key = "simulations"
    elif result_type == "calibration":
        dispatch_key = "calibrations"
    else:
        raise ValueError(f"Unknown result type: {result_type}")

    dispatch_kwargs = {dispatch_key: results, "output_config": output_config}

    output_dict = dispatch_output_generator(**dispatch_kwargs)

    if output_dict is None:
        raise ValueError("dispatch_output_generator returned None - no outputs generated")

    # Count total output objects
    total_outputs = sum(len(output_objects) for output_objects in output_dict.values())
    logger.info(f"Output dictionary contains {len(output_dict)} keys with {total_outputs} OutputObject instances")
    for output_key, output_objects in output_dict.items():
        logger.debug(f"  - {output_key}: {len(output_objects)} files")
        for obj in output_objects:
            logger.debug(f"    - {obj.name} ({obj.output_type})")

    return output_dict


def save_output_files(output_dict: dict, logger: logging.Logger) -> None:
    """Save output files to storage.

    Parameters
    ----------
    output_dict : dict
        Dictionary mapping output keys to lists of OutputObject instances
    logger : logging.Logger
        Logger instance for output

    Raises
    ------
    Exception
        If any file save operation fails
    """
    from epymodelingsuite.schema.output import TabularOutputTypeEnum, FigureOutputTypeEnum

    logger.info("Saving output files to storage")

    # Flatten output_dict to get all OutputObjects
    all_outputs = [obj for objects in output_dict.values() for obj in objects]

    files_saved = 0
    for output_obj in all_outputs:
        # Save byte-based outputs (CSVBytes, PNG, PDF, SVG)
        if output_obj.output_type in (
            TabularOutputTypeEnum.CSVBytes,
            FigureOutputTypeEnum.PNG,
            FigureOutputTypeEnum.PDF,
            FigureOutputTypeEnum.SVG,
        ):
            output_path = storage.get_path("outputs", output_obj.name)
            logger.debug(f"Saving: {output_path}")
            storage.save_bytes(output_path, output_obj.data)
            logger.debug(f"Saved: {len(output_obj.data):,} bytes")
            files_saved += 1
        # Skip in-memory formats (DataFrame, MPLFigure)
        else:
            logger.debug(f"Skipping in-memory output: {output_obj.name} ({output_obj.output_type})")

    logger.info(f"Successfully saved {files_saved} output files to storage")


def aggregate_telemetry(num_tasks: int, logger: logging.Logger) -> None:
    """Load all stage telemetries and create workflow summary.

    Parameters
    ----------
    num_tasks : int
        Number of runner tasks to load telemetry from
    logger : logging.Logger
        Logger instance for output

    Notes
    -----
    This function is called in the finally block and continues even if
    individual telemetry files are missing.
    """
    logger.info("Aggregating telemetry summaries")

    # Load builder telemetry
    try:
        builder_telemetry_data = storage.load_json(
            storage.get_path("summaries", "json", "builder_summary.json")
        )
        builder_telemetry = ExecutionTelemetry.from_dict(builder_telemetry_data)
        logger.debug("Loaded builder telemetry")
    except (FileNotFoundError, Exception) as e:
        logger.warning(f"Could not load builder telemetry: {e}")
        builder_telemetry = None

    # Load runner telemetries
    runner_telemetries = []
    for i in range(num_tasks):
        try:
            runner_telemetry_data = storage.load_json(
                storage.get_path("summaries", "json", f"runner_{i:0{INDEX_WIDTH}d}_summary.json")
            )
            runner_telemetries.append(ExecutionTelemetry.from_dict(runner_telemetry_data))
        except (FileNotFoundError, Exception):
            pass
    logger.info(f"Loaded {len(runner_telemetries)} runner telemetries")

    # Load output telemetry
    try:
        output_telemetry_data = storage.load_json(
            storage.get_path("summaries", "json", "output_summary.json")
        )
        output_telemetry = ExecutionTelemetry.from_dict(output_telemetry_data)
        logger.debug("Loaded output telemetry")
    except (FileNotFoundError, Exception) as e:
        logger.warning(f"Could not load output telemetry: {e}")
        output_telemetry = None

    # Create and save workflow telemetry
    try:
        # Create workflow telemetry from all stages
        workflow_telemetry = create_workflow_telemetry(
            builder_telemetry=builder_telemetry,
            runner_telemetries=runner_telemetries,
            output_telemetry=output_telemetry,
        )
        logger.debug("Created workflow telemetry")

        # Save workflow telemetry summary
        storage.save_telemetry_summary(workflow_telemetry, "workflow_summary")
    except Exception as e:
        logger.warning(f"Failed to create workflow telemetry: {e}")


def main() -> None:
    """Generate output files from runner results (Stage C).

    This stage:
    1. Loads output configuration for the experiment
    2. Loads all result pickle files from Stage B
    3. Generates formatted output files using dispatch_output_generator
    4. Saves output CSV.gz files to storage
    5. Aggregates telemetry from all stages into workflow summary

    Environment Variables
    ---------------------
    EXP_ID : str (required)
        Experiment identifier
    RUN_ID : str (optional)
        Run identifier (defaults to "unknown")
    NUM_TASKS : str (optional)
        Number of result files to load (defaults to 1 if not in config)
    EXECUTION_MODE : str
        Storage mode: "cloud" (GCS) or "local" (filesystem)

    Outputs
    -------
    Saves to storage:
        - outputs/*.csv.gz : Formatted output files (quantiles, trajectories, etc.)
        - summaries/json/output_summary.json : Output stage telemetry
        - summaries/json/workflow_summary.json : Aggregated workflow telemetry

    Raises
    ------
    ValueError
        If configuration is invalid or if result loading/generation fails
    SystemExit
        Exits with code 1 on any fatal error
    """
    # Get configuration
    config = storage.get_config()

    # Setup logger with context
    logger = setup_logger(
        "output",
        exp_id=config["exp_id"],
        run_id=config["run_id"],
    )

    logger.info("Starting Stage C: Output Generation")
    logger.info(
        "Storage configuration",
        extra={
            "mode": config["mode"],
            "dir_prefix": config["dir_prefix"],
            "bucket": config.get("bucket", "N/A"),
        },
    )

    # Get number of tasks from environment or config
    num_tasks = int(os.getenv("NUM_TASKS", config.get("num_tasks", 1)))
    logger.info(f"Number of tasks: {num_tasks}")

    try:
        # Load and validate configuration
        output_config = load_configuration(config, logger)

        # Load all result files from Stage B
        results, result_type = load_all_results(num_tasks, logger)

        # Wrap output generation in telemetry context
        with ExecutionTelemetry() as output_telemetry:
            # Generate output files using dispatcher
            output_dict = generate_outputs(results, result_type, output_config, logger)

            # Save output files to storage
            save_output_files(output_dict, logger)

            # Save output telemetry summary
            storage.save_telemetry_summary(output_telemetry, "output_summary")

        logger.info("Stage C complete!")

    except Exception as e:
        handle_stage_error("Stage C (Output)", e, logger)

    finally:
        # ALWAYS aggregate summaries (even on failure)
        aggregate_telemetry(num_tasks, logger)


if __name__ == "__main__":
    main()
