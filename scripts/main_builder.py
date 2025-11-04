#!/usr/bin/env python3
"""
Stage A: Generate all input files for parallel processing.
Creates N pickled input files and uploads them to storage (GCS or local).
"""

import os
import sys

import dill  # Use dill instead of pickle for better serialization support

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util import storage
from util.config import load_all_configs, resolve_configs
from util.logger import setup_logger
from util.error_handling import handle_stage_error

from flumodelingsuite.dispatcher import dispatch_builder
from flumodelingsuite.telemetry import ExecutionTelemetry

# Task index formatting (supports up to 99999 tasks)
INDEX_WIDTH = 5


def build_and_save_dispatch_outputs(
    basemodel_config,
    sampling_config,
    calibration_config,
    logger,
) -> int:
    """Build dispatch outputs and save as pickled input files to storage.

    Parameters
    ----------
    basemodel_config
        Loaded basemodel configuration
    sampling_config
        Loaded sampling configuration (optional, can be None)
    calibration_config
        Loaded calibration configuration (optional, can be None)
    logger
        Logger instance for output

    Returns
    -------
    int
        Number of input files saved
    """
    logger.info("Building dispatch")

    # Wrap builder in telemetry context
    with ExecutionTelemetry() as builder_telemetry:
        # Build dispatch kwargs with available configs
        dispatch_kwargs = {"basemodel_config": basemodel_config}

        if sampling_config is not None:
            dispatch_kwargs["sampling_config"] = sampling_config
            logger.info("Using sampling config")

        if calibration_config is not None:
            dispatch_kwargs["calibration_config"] = calibration_config
            logger.info("Using calibration config")

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
            path = storage.get_path("builder-artifacts", f"input_{idx:0{INDEX_WIDTH}d}.pkl")
            storage.save_bytes(path, data)
            logger.debug(f"Saved: {path} ({len(data):,} bytes)")

        # Save telemetry summary
        storage.save_telemetry_summary(builder_telemetry, "builder_summary")

        return len(outputs)


def main() -> None:
    """Generate dispatch inputs for parallel processing (Stage A)."""
    try:
        # Get configuration
        config = storage.get_config()

        # Setup logger with context
        logger = setup_logger(
            "builder",
            exp_id=config["exp_id"],
            run_id=config["run_id"],
        )

        logger.info("Starting Stage A: Generating dispatch inputs")
        logger.info(
            "Storage configuration",
            extra={
                "mode": config["mode"],
                "dir_prefix": config["dir_prefix"],
                "bucket": config.get("bucket", "N/A"),
            }
        )

        # Resolve config files for this experiment
        logger.info(f"Resolving config files for exp_id: {config['exp_id']}")
        config_files = resolve_configs(config["exp_id"])

        logger.debug(
            "Found config files",
            extra={
                "basemodel": config_files["basemodel"],
                "sampling": config_files["sampling"],
                "calibration": config_files["calibration"],
                "output": config_files["output"],
            }
        )

        # Load all configs and validate consistency
        basemodel_config, sampling_config, calibration_config, output_config = load_all_configs(
            config_files
        )

        # Build dispatch and save input files
        num_files = build_and_save_dispatch_outputs(
            basemodel_config, sampling_config, calibration_config, logger
        )

        logger.info(f"Stage A complete: {num_files} input files saved", extra={"num_files": num_files})

    except Exception as e:
        handle_stage_error("Stage A (Builder)", e, logger)


if __name__ == "__main__":
    main()
