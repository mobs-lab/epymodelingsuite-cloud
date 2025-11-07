"""XDG-compliant path management for epycloud."""

import os
from pathlib import Path


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

    Returns
    -------
    Path
        Path to config.yaml in the configuration directory.
    """
    return get_config_dir() / "config.yaml"


def get_secrets_file() -> Path:
    """
    Get path to secrets configuration file.

    Returns
    -------
    Path
        Path to secrets.yaml in the configuration directory.
    """
    return get_config_dir() / "secrets.yaml"


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

    Parameters
    ----------
    environment : str
        Environment name (e.g., dev, prod, local).

    Returns
    -------
    Path
        Path to environments/{environment}.yaml in the configuration directory.
    """
    return get_config_dir() / "environments" / f"{environment}.yaml"


def get_profile_file(profile: str) -> Path:
    """
    Get path to profile-specific configuration file.

    Parameters
    ----------
    profile : str
        Profile name (e.g., flu, covid, rsv).

    Returns
    -------
    Path
        Path to profiles/{profile}.yaml in the configuration directory.
    """
    return get_config_dir() / "profiles" / f"{profile}.yaml"


def get_project_config_file() -> Path:
    """
    Get path to project-local configuration file.

    Returns
    -------
    Path
        Path to ./epycloud.yaml in the current working directory.
    """
    return Path.cwd() / "epycloud.yaml"
