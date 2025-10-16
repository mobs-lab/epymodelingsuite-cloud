#!/usr/bin/env python3
"""
Stage A: Generate all input files for parallel processing.
Creates N pickled input files and uploads them to storage (GCS or local).
"""

import os
import sys
from pathlib import Path
from typing import Optional

import dill  # Use dill instead of pickle for better serialization support

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util import storage

from flumodelingsuite.config_loader import (
    load_basemodel_config_from_file,
    load_sampling_config_from_file,
    load_calibration_config_from_file,
)
from flumodelingsuite.utils import identify_config_type

from flumodelingsuite.workflow_dispatcher import dispatch_builder

from flumodelingsuite.validation.general_validator import validate_modelset_consistency


def load_all_configs(
    config_paths: dict[str, Optional[str]], validate_consistency: bool = True
) -> tuple:
    """
    Load all configuration files and optionally validate consistency.

    Args:
        config_paths: Dictionary from resolve_configs with paths to config files
        validate_consistency: Whether to validate modelset consistency (default: True)
                            Validates basemodel against sampling and/or calibration if present

    Returns:
        Tuple of (basemodel_config, sampling_config, calibration_config)
        - basemodel_config: Always present (required)
        - sampling_config: Optional, None if not found
        - calibration_config: Optional, None if not found

    Raises:
        ValueError: If basemodel config is not found (required)
    """
    # Load basemodel config (required)
    if config_paths["basemodel"] is None:
        raise ValueError("Basemodel config is required but was not found")

    print(f"\nLoading basemodel config: {config_paths['basemodel']}")
    basemodel_config = load_basemodel_config_from_file(config_paths["basemodel"])

    # Load sampling config (optional)
    sampling_config = None
    if config_paths["sampling"] is not None:
        print(f"Loading sampling config: {config_paths['sampling']}")
        sampling_config = load_sampling_config_from_file(config_paths["sampling"])

    # Load calibration config (optional)
    calibration_config = None
    if config_paths["calibration"] is not None:
        print(f"Loading calibration config: {config_paths['calibration']}")
        calibration_config = load_calibration_config_from_file(
            config_paths["calibration"]
        )

    # Validate modelset consistency if any modelset config is provided
    if validate_consistency:
        if sampling_config is not None:
            print("Validating modelset consistency (basemodel + sampling)...")
            validate_modelset_consistency(basemodel_config, sampling_config)
        if calibration_config is not None:
            print("Validating modelset consistency (basemodel + calibration)...")
            validate_modelset_consistency(basemodel_config, calibration_config)

    return basemodel_config, sampling_config, calibration_config


def build_and_save_dispatch_outputs(
    basemodel_config,
    sampling_config,
    calibration_config,
) -> int:
    """
    Build dispatch outputs and save as pickled input files to storage.

    Args:
        basemodel_config: Loaded basemodel configuration
        sampling_config: Loaded sampling configuration (optional, can be None)
        calibration_config: Loaded calibration configuration (optional, can be None)

    Returns:
        Number of input files saved
    """
    print("\nBuilding dispatch...")

    # Build dispatch kwargs with available configs
    dispatch_kwargs = {"basemodel_config": basemodel_config}

    if sampling_config is not None:
        dispatch_kwargs["sampling_config"] = sampling_config
        print("  Using sampling config")

    if calibration_config is not None:
        dispatch_kwargs["calibration_config"] = calibration_config
        print("  Using calibration config")

    # Build dispatch outputs
    outputs = dispatch_builder(**dispatch_kwargs)

    # Ensure outputs is a list
    if not isinstance(outputs, list):
        outputs = [outputs]

    # Save each output as a pickled input file
    for idx, output in enumerate(outputs):
        # Pickle the data using dill
        data = dill.dumps(output)

        # Upload to storage (GCS or local)
        path = storage.get_path("inputs", f"input_{idx:04d}.pkl")
        storage.save_bytes(path, data)
        print(f"  Saved: {path} ({len(data)} bytes)")

    return len(outputs)


def resolve_configs(
    exp_id: str, config_dir: str = "/data/forecast/experiments"
) -> dict[str, Optional[str]]:
    """
    Resolve config files for an experiment by parsing YAML structure.

    Searches for YAML files in {config_dir}/{exp_id}/config/ and identifies their type by
    parsing the file structure:
    - Files with 'model' key -> basemodel config
    - Files with 'modelset.sampling' -> sampling config
    - Files with 'modelset.calibration' -> calibration config

    Args:
        exp_id: Experiment ID (e.g., 'test-sim', 'flu_round05')
        config_dir: Base directory for experiments (default: '/data/forecast/experiments')

    Returns:
        Dictionary with keys 'basemodel', 'sampling', 'calibration' mapping to file paths or None
        Example: {'basemodel': '/path/to/config.yaml', 'sampling': None, 'calibration': None}

    Raises:
        FileNotFoundError: If the exp_id directory doesn't exist or no YAML files are found
        ValueError: If multiple files of the same type are found
    """
    exp_config_dir = Path(config_dir) / exp_id / "config"

    if not exp_config_dir.exists():
        raise FileNotFoundError(
            f"Config directory not found for exp_id '{exp_id}': {exp_config_dir}"
        )

    # Find all YAML files in the directory
    yaml_files = list(exp_config_dir.glob("*.yml")) + list(
        exp_config_dir.glob("*.yaml")
    )

    if not yaml_files:
        raise FileNotFoundError(
            f"No YAML files found in config directory: {exp_config_dir}"
        )

    # Initialize result dictionary
    configs = {
        "basemodel": None,
        "sampling": None,
        "calibration": None,
    }

    # Identify each YAML file by parsing its structure
    unidentified_files = []

    for yaml_file in yaml_files:
        try:
            config_type = identify_config_type(str(yaml_file))
        except Exception as e:
            # Log parsing errors but continue
            unidentified_files.append((yaml_file.name, str(e)))
            continue

        # Skip files that don't match any known type
        if config_type is None:
            unidentified_files.append((yaml_file.name, "Unknown config structure"))
            continue

        # Check for duplicates
        if configs[config_type] is not None:
            raise ValueError(
                f"Multiple {config_type} config files found in {exp_config_dir}: "
                f"{Path(configs[config_type]).name} and {yaml_file.name}"
            )

        configs[config_type] = str(yaml_file)

    # Log unidentified files as warnings (not errors)
    if unidentified_files:
        print(f"  Warning: Could not identify {len(unidentified_files)} file(s):")
        for filename, reason in unidentified_files:
            print(f"    - {filename}: {reason}")

    return configs


def main():
    # Get configuration
    config = storage.get_config()

    print("Starting Stage A: Generating dispatch inputs")
    print(f"  Storage mode: {config['mode']}")
    print(f"  Dir prefix: {config['dir_prefix']}")
    print(f"  Experiment ID: {config['exp_id']}")
    print(f"  Run ID: {config['run_id']}")
    if config["mode"] == "cloud":
        print(f"  Bucket: {config['bucket']}")

    # Resolve config files for this experiment
    print(f"\nResolving config files for exp_id: {config['exp_id']}")
    config_files = resolve_configs(config["exp_id"])

    print("  Found configs:")
    print(f"    Basemodel: {config_files['basemodel']}")
    print(f"    Sampling: {config_files['sampling']}")
    print(f"    Calibration: {config_files['calibration']}")

    # Load all configs and validate consistency
    basemodel_config, sampling_config, calibration_config = load_all_configs(
        config_files
    )

    # Build dispatch and save input files
    num_files = build_and_save_dispatch_outputs(
        basemodel_config, sampling_config, calibration_config
    )

    print(f"\nStage A complete: {num_files} input files saved")


if __name__ == "__main__":
    main()
