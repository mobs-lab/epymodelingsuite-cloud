#!/usr/bin/env python3
"""
Stage C: Generate output files from runner results.
Loads all result pickle files from Stage B, generates formatted outputs using
dispatch_output_generator, and saves CSV.gz files to storage.
"""

import os
import sys
from pathlib import Path

import dill

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util import storage

from flumodelingsuite.config_loader import load_output_config_from_file
from flumodelingsuite.dispatcher import dispatch_output_generator
from flumodelingsuite.utils import identify_config_type


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


def load_all_results(num_tasks: int) -> tuple[list, str]:
    """Load all result pickle files from Stage B.

    Parameters
    ----------
    num_tasks : int
        Number of result files to load

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

    print(f"Loading {num_tasks} result files from Stage B...")

    # First pass: Check which files exist and load them
    for i in range(num_tasks):
        result_path = storage.get_path("runner-artifacts", f"result_{i:04d}.pkl")
        print(f"  Checking: {result_path}")

        try:
            raw_data = storage.load_bytes(result_path)
            result = dill.loads(raw_data)
            results.append(result)

            # Determine result type from first result
            if result_type is None:
                result_type = detect_result_type(result)
                print(f"  Detected result type: {result_type}")

            print(f"    Loaded: {len(raw_data)} bytes")
        except FileNotFoundError:
            print(f"    MISSING: File not found")
            missing_tasks.append(i)
        except Exception as e:
            print(f"    FAILED: {type(e).__name__}: {e}")
            failed_tasks.append(i)

    # Report results
    successful = len(results)
    total_failed = len(missing_tasks) + len(failed_tasks)

    print(f"\nLoad Summary:")
    print(f"  Successfully loaded: {successful}/{num_tasks}")
    print(f"  Missing files: {len(missing_tasks)}")
    print(f"  Failed to load: {len(failed_tasks)}")

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

    print(f"\nSuccessfully loaded {len(results)} {result_type} results")
    return results, result_type


def resolve_output_config(exp_id: str, config_dir: str = "/data/forecast/experiments") -> str | None:
    """Resolve output config file for an experiment (same pattern as resolve_configs in main_builder.py).

    Parameters
    ----------
    exp_id : str
        Experiment ID
    config_dir : str, optional
        Base directory for experiments (default: '/data/forecast/experiments')

    Returns
    -------
    str | None
        Path to output config file or None if not found
    """
    exp_config_dir = Path(config_dir) / exp_id / "config"

    if not exp_config_dir.exists():
        return None

    # Find all YAML files
    yaml_files = list(exp_config_dir.glob("*.yml")) + list(exp_config_dir.glob("*.yaml"))

    # Use identify_config_type to find output config
    for yaml_file in yaml_files:
        try:
            config_type = identify_config_type(str(yaml_file))
            if config_type == "output":
                return str(yaml_file)
        except Exception:
            continue

    return None


def main():
    # Get configuration
    config = storage.get_config()

    print("Starting Stage C: Output Generation")
    print(f"  Storage mode: {config['mode']}")
    print(f"  Dir prefix: {config['dir_prefix']}")
    print(f"  Experiment ID: {config['exp_id']}")
    print(f"  Run ID: {config['run_id']}")
    if config["mode"] == "cloud":
        print(f"  Bucket: {config['bucket']}")

    # Get number of tasks from environment or config
    num_tasks = int(os.getenv("NUM_TASKS", config.get("num_tasks", 1)))
    print(f"  Number of tasks: {num_tasks}")

    # Load output configuration (auto-detect, same pattern as stages A and B)
    output_config_path = resolve_output_config(config["exp_id"])

    if not output_config_path:
        exp_config_dir = Path("/data/forecast/experiments") / config["exp_id"] / "config"
        print("ERROR: No output config found")
        print(f"  Searched in: {exp_config_dir}")
        print("  Looking for YAML files with 'outputs' key")
        print("Please add output.yaml with 'outputs' key to your experiment config directory")
        sys.exit(1)

    print(f"Output config: {output_config_path}")
    try:
        output_config = load_output_config_from_file(output_config_path)
        print("  Output config loaded successfully")
    except Exception as e:
        print(f"ERROR: Failed to load output config: {e}")
        raise

    # Load all result files from Stage B
    try:
        results, result_type = load_all_results(num_tasks)
    except Exception as e:
        print(f"ERROR: Failed to load results: {e}")
        raise

    # Generate outputs using dispatch_output_generator
    print(f"\nGenerating outputs for {result_type}...")
    try:
        # Prepare kwargs for dispatcher based on result type
        # Note: Registry expects plural form (simulations/calibrations)
        if result_type == "simulation":
            dispatch_key = "simulations"
        elif result_type == "calibration":
            dispatch_key = "calibrations"
        else:
            raise ValueError(f"Unknown result type: {result_type}")

        dispatch_kwargs = {
            dispatch_key: results,
            "outputs": output_config.outputs
        }

        output_dict = dispatch_output_generator(**dispatch_kwargs)

        if output_dict is None:
            raise ValueError("dispatch_output_generator returned None - no outputs generated")

        print(f"  Generated {len(output_dict)} output files")
        for filename in output_dict.keys():
            print(f"    - {filename}")
    except Exception as e:
        print(f"ERROR: Output generation failed: {e}")
        raise

    # Save output files to storage
    print("\nSaving output files to storage...")
    try:
        for filename, gzipped_data in output_dict.items():
            output_path = storage.get_path("outputs", filename)
            print(f"  Saving: {output_path}")
            storage.save_bytes(output_path, gzipped_data)
            print(f"    Saved: {len(gzipped_data)} bytes")

        print(f"\nSuccessfully saved {len(output_dict)} output files")
    except Exception as e:
        print(f"ERROR: Failed to save outputs: {e}")
        raise

    print("\nStage C complete!")


if __name__ == "__main__":
    main()
