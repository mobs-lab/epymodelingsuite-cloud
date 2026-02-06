"""XDG-compliant path management for epycloud."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """
    Get the configuration directory following XDG Base Directory spec.

    Returns
    -------
    Path
        Path to ~/.config/epymodelingsuite-cloud/ or $XDG_CONFIG_HOME/epymodelingsuite-cloud/.
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        base = Path(xdg_config_home)
    else:
        base = Path.home() / ".config"

    return base / "epymodelingsuite-cloud"


def get_data_dir() -> Path:
    """
    Get the data directory following XDG Base Directory spec.

    Returns
    -------
    Path
        Path to ~/.local/share/epymodelingsuite-cloud/ or $XDG_DATA_HOME/epymodelingsuite-cloud/.
    """
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        base = Path(xdg_data_home)
    else:
        base = Path.home() / ".local" / "share"

    return base / "epymodelingsuite-cloud"


def get_cache_dir() -> Path:
    """
    Get the cache directory following XDG Base Directory spec.

    Returns
    -------
    Path
        Path to ~/.cache/epymodelingsuite-cloud/ or $XDG_CACHE_HOME/epymodelingsuite-cloud/.
    """
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache_home:
        base = Path(xdg_cache_home)
    else:
        base = Path.home() / ".cache"

    return base / "epymodelingsuite-cloud"


def ensure_config_dir() -> Path:
    """
    Ensure configuration directory exists and return it.

    Creates the config directory and its subdirectories (environments, profiles)
    if they don't exist.

    Returns
    -------
    Path
        Path to config directory.
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (config_dir / "environments").mkdir(exist_ok=True)
    (config_dir / "profiles").mkdir(exist_ok=True)

    return config_dir


def ensure_data_dir() -> Path:
    """
    Ensure data directory exists and return it.

    Creates the data directory if it doesn't exist.

    Returns
    -------
    Path
        Path to data directory.
    """
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def ensure_cache_dir() -> Path:
    """
    Ensure cache directory exists and return it.

    Creates the cache directory if it doesn't exist.

    Returns
    -------
    Path
        Path to cache directory.
    """
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_config_file() -> Path:
    """
    Get path to main configuration file.

    Checks for .yaml first, falls back to .yml if .yaml doesn't exist.
    If both extensions exist, returns .yaml and logs a warning.

    Returns
    -------
    Path
        Path to config.yaml (or config.yml) in the configuration directory.
    """
    return _resolve_yaml_file(get_config_dir(), "config")


def get_secrets_file() -> Path:
    """
    Get path to secrets configuration file.

    Checks for .yaml first, falls back to .yml if .yaml doesn't exist.
    If both extensions exist, returns .yaml and logs a warning.

    Returns
    -------
    Path
        Path to secrets.yaml (or secrets.yml) in the configuration directory.
    """
    return _resolve_yaml_file(get_config_dir(), "secrets")


def get_active_profile_file() -> Path:
    """
    Get path to active profile marker file.

    This file contains the name of the currently active profile.

    Returns
    -------
    Path
        Path to active_profile file in the configuration directory.
    """
    return get_config_dir() / "active_profile"


def get_environment_file(environment: str) -> Path:
    """
    Get path to environment-specific configuration file.

    Checks for .yaml first, falls back to .yml if .yaml doesn't exist.
    If both extensions exist, returns .yaml and logs a warning.

    Parameters
    ----------
    environment : str
        Environment name (e.g., dev, prod, local).

    Returns
    -------
    Path
        Path to environments/{environment}.yaml (or .yml) in the configuration directory.
    """
    return _resolve_yaml_file(get_config_dir() / "environments", environment)


def list_environments() -> list[str]:
    """
    List all available environment names.

    Scans the environments directory for .yaml and .yml files and returns
    their names (without extension). Deduplicates by stem, preferring .yaml.

    Returns
    -------
    list[str]
        List of environment names, or empty list if environments directory
        doesn't exist.

    Examples
    --------
    >>> list_environments()
    ['dev', 'prod', 'local']
    """
    envs_dir = get_config_dir() / "environments"
    if not envs_dir.exists():
        return []

    return [f.stem for f in _list_yaml_files(envs_dir)]


def get_profile_file(profile: str) -> Path:
    """
    Get path to profile-specific configuration file.

    Checks for .yaml first, falls back to .yml if .yaml doesn't exist.
    If both extensions exist, returns .yaml and logs a warning.

    Parameters
    ----------
    profile : str
        Profile name (e.g., flu, covid, rsv).

    Returns
    -------
    Path
        Path to profiles/{profile}.yaml (or .yml) in the configuration directory.
    """
    return _resolve_yaml_file(get_config_dir() / "profiles", profile)


def _resolve_yaml_file(directory: Path, name: str) -> Path:
    """
    Resolve a YAML file path, supporting both .yaml and .yml extensions.

    Returns the .yaml path by default. If .yaml doesn't exist but .yml does,
    returns .yml. If both exist, returns .yaml and logs a warning.

    Parameters
    ----------
    directory : Path
        Directory containing the YAML file.
    name : str
        File stem (without extension).

    Returns
    -------
    Path
        Resolved path to the YAML file.
    """
    yaml_path = directory / f"{name}.yaml"
    yml_path = directory / f"{name}.yml"

    if yaml_path.exists() and yml_path.exists():
        logger.warning(
            "Both %s.yaml and %s.yml exist in %s; using .yaml",
            name,
            name,
            directory,
        )
        return yaml_path

    if not yaml_path.exists() and yml_path.exists():
        return yml_path

    return yaml_path


def _list_yaml_files(directory: Path) -> list[Path]:
    """
    List YAML files in a directory, supporting both .yaml and .yml extensions.

    Deduplicates by stem (preferring .yaml over .yml) and logs a warning
    when both extensions exist for the same name.

    Parameters
    ----------
    directory : Path
        Directory to scan for YAML files.

    Returns
    -------
    list[Path]
        Sorted list of YAML file paths, deduplicated by stem.
    """
    yaml_files = {f.stem: f for f in directory.glob("*.yml")}
    # .yaml overrides .yml for same stem
    for f in directory.glob("*.yaml"):
        if f.stem in yaml_files:
            logger.warning(
                "Both %s.yaml and %s.yml exist in %s; using .yaml",
                f.stem,
                f.stem,
                directory,
            )
        yaml_files[f.stem] = f

    return sorted(yaml_files.values(), key=lambda f: f.stem)


def get_project_config_file() -> Path:
    """
    Get path to project-local configuration file.

    Returns
    -------
    Path
        Path to ./epycloud.yaml in the current working directory.
    """
    return Path.cwd() / "epycloud.yaml"
