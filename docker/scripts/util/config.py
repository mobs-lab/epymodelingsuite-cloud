"""Configuration file resolution and loading utilities."""

import logging
from pathlib import Path

from epymodelingsuite.config_loader import (
    load_basemodel_config_from_file,
    load_calibration_config_from_file,
    load_output_config_from_file,
    load_sampling_config_from_file,
)
from epymodelingsuite.schema.general import validate_cross_config_consistency
from epymodelingsuite.utils import identify_config_type

# Module-level logger for utility logging
_logger = logging.getLogger(__name__)


def resolve_configs(
    exp_id: str, config_dir: str = "/data/forecast/experiments"
) -> dict[str, str | None]:
    """Resolve config files for an experiment by parsing YAML structure.

    Searches for YAML files in {config_dir}/{exp_id}/config/ and identifies their type by
    parsing the file structure:
    - Files with 'model' key -> basemodel config
    - Files with 'modelset.sampling' -> sampling config
    - Files with 'modelset.calibration' -> calibration config
    - Files with 'output' -> output config

    Supports nested directory structures by searching for the experiment in subdirectories
    if not found directly under config_dir.

    Parameters
    ----------
    exp_id : str
        Experiment ID (e.g., 'test-sim', 'flu_round05')
    config_dir : str, optional
        Base directory for experiments (default: '/data/forecast/experiments')

    Returns
    -------
    dict[str, Optional[str]]
        Dictionary with keys 'basemodel', 'sampling', 'calibration', 'output' mapping to file paths or None
        Example: {'basemodel': '/path/to/config.yaml', 'sampling': None, 'calibration': None, 'output': None}

    Raises
    ------
    FileNotFoundError
        If the exp_id directory doesn't exist or no YAML files are found
    ValueError
        If multiple files of the same type are found
    """
    exp_config_dir = Path(config_dir) / exp_id / "config"

    # If direct path doesn't exist, search in subdirectories
    if not exp_config_dir.exists():
        _logger.debug(f"Direct path not found: {exp_config_dir}, searching in subdirectories...")
        base_dir = Path(config_dir)

        # Search for exp_id in subdirectories (e.g., test/test-flu-projection-small)
        found_paths = list(base_dir.glob(f"*/{exp_id}/config"))

        if not found_paths:
            raise FileNotFoundError(
                f"Config directory not found for exp_id '{exp_id}': {exp_config_dir}"
            )

        if len(found_paths) > 1:
            raise ValueError(
                f"Multiple config directories found for exp_id '{exp_id}': {found_paths}"
            )

        exp_config_dir = found_paths[0]
        _logger.info(f"Found config directory: {exp_config_dir}")

    if not exp_config_dir.exists():
        raise FileNotFoundError(
            f"Config directory not found for exp_id '{exp_id}': {exp_config_dir}"
        )

    # Find all YAML files in the directory
    yaml_files = list(exp_config_dir.glob("*.yml")) + list(exp_config_dir.glob("*.yaml"))

    if not yaml_files:
        raise FileNotFoundError(f"No YAML files found in config directory: {exp_config_dir}")

    # Initialize result dictionary
    configs = {
        "basemodel": None,
        "sampling": None,
        "calibration": None,
        "output": None,
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
        _logger.warning(f"Could not identify {len(unidentified_files)} file(s)")
        for filename, reason in unidentified_files:
            _logger.warning(f"  - {filename}: {reason}")

    return configs


def load_all_configs(
    config_paths: dict[str, str | None], validate_consistency: bool = True
) -> tuple:
    """Load all configuration files and optionally validate consistency.

    Parameters
    ----------
    config_paths : dict[str, Optional[str]]
        Dictionary from resolve_configs with paths to config files
    validate_consistency : bool, optional
        Whether to validate config consistency (default: True)
        Validates consistency across basemodel, sampling, calibration, and output configs
        when any of them (sampling/calibration/output) are present

    Returns
    -------
    tuple
        Tuple of (basemodel_config, sampling_config, calibration_config, output_config)
        - basemodel_config: Always present (required)
        - sampling_config: Optional, None if not found
        - calibration_config: Optional, None if not found
        - output_config: Optional, None if not found

    Raises
    ------
    ValueError
        If basemodel config is not found (required)
    """
    # Load basemodel config (required)
    if config_paths["basemodel"] is None:
        raise ValueError("Basemodel config is required but was not found")

    _logger.debug(f"Loading basemodel config: {config_paths['basemodel']}")
    basemodel_config = load_basemodel_config_from_file(config_paths["basemodel"])

    # Load sampling config (optional)
    sampling_config = None
    if config_paths["sampling"] is not None:
        _logger.debug(f"Loading sampling config: {config_paths['sampling']}")
        sampling_config = load_sampling_config_from_file(config_paths["sampling"])

    # Load calibration config (optional)
    calibration_config = None
    if config_paths["calibration"] is not None:
        _logger.debug(f"Loading calibration config: {config_paths['calibration']}")
        calibration_config = load_calibration_config_from_file(config_paths["calibration"])

    # Load output config (optional)
    output_config = None
    if config_paths["output"] is not None:
        _logger.debug(f"Loading output config: {config_paths['output']}")
        output_config = load_output_config_from_file(config_paths["output"])

    # Validate consistency across all configs if any modelset/output config is provided
    if validate_consistency and (sampling_config is not None or calibration_config is not None):
        _logger.debug("Validating config consistency across all provided configs")
        # validate_cross_config_consistency expects either sampling or calibration, not both
        modelset_config = sampling_config if sampling_config is not None else calibration_config
        validate_cross_config_consistency(basemodel_config, modelset_config, output_config)

    return basemodel_config, sampling_config, calibration_config, output_config
