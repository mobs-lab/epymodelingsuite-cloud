"""Configuration loader with environment and profile support."""

import os
from pathlib import Path
from typing import Any

import yaml

from epycloud.lib.paths import (
    get_active_profile_file,
    get_config_file,
    get_environment_file,
    get_profile_file,
    get_project_config_file,
    get_secrets_file,
)


class ConfigLoader:
    """
    Load and merge configuration from multiple sources.

    The ConfigLoader manages hierarchical configuration loading from:
    1. Base config (config.yaml)
    2. Environment config (environments/{env}.yaml)
    3. Profile config (profiles/{profile}.yaml)
    4. Project config (./epycloud.yaml)
    5. Secrets (secrets.yaml)
    6. Environment variables (EPYCLOUD_*)

    Attributes
    ----------
    environment : str
        Environment name (dev, prod, local).
    profile : str or None
        Profile name (flu, covid, rsv, etc.).
    config_path : Path
        Path to base configuration file.
    """

    def __init__(
        self,
        environment: str = "default",
        profile: str | None = None,
        config_path: Path | None = None,
    ):
        """
        Initialize configuration loader.

        Parameters
        ----------
        environment : str, optional
            Environment name (default, or custom), by default "default".
        profile : str or None, optional
            Profile name (flu, covid, rsv, etc.). If None, uses active profile
            from active_profile file, by default None.
        config_path : Path or None, optional
            Path to base config file. If None, uses default config.yaml location,
            by default None.
        """
        self.environment = environment
        self.profile = profile or self._get_active_profile()
        self.config_path = config_path or get_config_file()

    def _get_active_profile(self) -> str | None:
        """
        Get the currently active profile from the active_profile marker file.

        Returns
        -------
        str or None
            Active profile name if set, None otherwise.
        """
        active_profile_file = get_active_profile_file()
        if active_profile_file.exists():
            return active_profile_file.read_text().strip()
        return None

    def _load_yaml_file(self, path: Path) -> dict:
        """
        Load and parse a YAML configuration file.

        Parameters
        ----------
        path : Path
            Path to YAML file to load.

        Returns
        -------
        dict
            Parsed YAML content, or empty dict if file doesn't exist.

        Raises
        ------
        ValueError
            If YAML file contains invalid syntax.
        """
        if not path.exists():
            return {}

        try:
            with open(path) as f:
                content = yaml.safe_load(f)
                return content if content else {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}")

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """
        Deep merge two dictionaries recursively.

        Nested dictionaries are merged recursively. For non-dict values,
        the override value replaces the base value.

        Parameters
        ----------
        base : dict
            Base dictionary to merge into.
        override : dict
            Override dictionary with values to merge.

        Returns
        -------
        dict
            New dictionary with merged contents.
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _interpolate_templates(self, config: dict) -> dict:
        """
        Interpolate template variables in configuration values.

        Recursively replaces {environment} and {profile} placeholders
        in string values throughout the configuration dictionary.

        Parameters
        ----------
        config : dict
            Configuration dictionary with potential template placeholders.

        Returns
        -------
        dict
            Configuration with all template variables interpolated.
        """

        def interpolate_value(value: Any) -> Any:
            if isinstance(value, str):
                value = value.replace("{environment}", self.environment)
                if self.profile and isinstance(self.profile, str):
                    value = value.replace("{profile}", self.profile)
                return value
            elif isinstance(value, dict):
                return {k: interpolate_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [interpolate_value(item) for item in value]
            else:
                return value

        return interpolate_value(config)

    def _apply_env_overrides(self, config: dict) -> dict:
        """
        Apply environment variable overrides to configuration.

        Reads environment variables with EPYCLOUD_ prefix and applies them
        to the configuration. Variable names are converted from
        EPYCLOUD_SECTION_SUBSECTION_KEY format to nested dictionary paths.

        Parameters
        ----------
        config : dict
            Configuration dictionary to apply overrides to.

        Returns
        -------
        dict
            Configuration with environment variable overrides applied.
        """
        prefix = "EPYCLOUD_"

        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue

            # Parse key path
            key_path = env_key[len(prefix) :].lower().split("_")

            # Navigate to the right place in config
            current = config
            for key in key_path[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]

            # Set the value
            final_key = key_path[-1]
            current[final_key] = env_value

        return config

    def load(self) -> dict:
        """
        Load and merge configuration from all sources.

        Loads configuration files in hierarchical order with later sources
        overriding earlier ones. Also applies template interpolation and
        environment variable overrides.

        Merge order (lowest to highest priority):
        1. Base config (config.yaml)
        2. Environment config (environments/{env}.yaml)
        3. Profile config (profiles/{profile}.yaml)
        4. Project config (./epycloud.yaml)
        5. Secrets (secrets.yaml)
        6. Template interpolation ({environment}, {profile})
        7. Environment variables (EPYCLOUD_*)

        Returns
        -------
        dict
            Merged configuration dictionary with metadata section.
        """
        # Start with empty config
        config = {}
        profile_metadata = None

        # 1. Load base config
        config = self._deep_merge(config, self._load_yaml_file(self.config_path))

        # 2. Load environment config
        env_file = get_environment_file(self.environment)
        config = self._deep_merge(config, self._load_yaml_file(env_file))

        # 3. Load profile config
        if self.profile:
            profile_file = get_profile_file(self.profile)
            profile_config = self._load_yaml_file(profile_file)

            # Extract profile metadata if present
            if "profile" in profile_config:
                profile_metadata = profile_config.pop("profile")

            config = self._deep_merge(config, profile_config)

        # 4. Load project config (optional)
        project_config = get_project_config_file()
        config = self._deep_merge(config, self._load_yaml_file(project_config))

        # 5. Load secrets
        secrets_file = get_secrets_file()
        config = self._deep_merge(config, self._load_yaml_file(secrets_file))

        # 6. Interpolate templates
        config = self._interpolate_templates(config)

        # 7. Apply environment variable overrides
        config = self._apply_env_overrides(config)

        # Add metadata
        config["_meta"] = {
            "environment": self.environment,
            "profile": profile_metadata,
            "config_sources": self._get_loaded_sources(),
        }

        return config

    def _get_loaded_sources(self) -> list[str]:
        """
        Get list of configuration files that were loaded.

        Returns
        -------
        list of str
            List of config file paths that exist and were successfully loaded.
        """
        sources = []

        # Base config
        if self.config_path.exists():
            sources.append(str(self.config_path))

        # Environment config
        env_file = get_environment_file(self.environment)
        if env_file.exists():
            sources.append(str(env_file))

        # Profile config
        if self.profile:
            profile_file = get_profile_file(self.profile)
            if profile_file.exists():
                sources.append(str(profile_file))

        # Project config
        project_config = get_project_config_file()
        if project_config.exists():
            sources.append(str(project_config))

        # Secrets
        secrets_file = get_secrets_file()
        if secrets_file.exists():
            sources.append(str(secrets_file))

        return sources


def get_config_value(config: dict, key_path: str, default: Any = None) -> Any:
    """
    Get configuration value using dot notation path.

    Navigates through nested dictionaries using dot-separated keys.

    Parameters
    ----------
    config : dict
        Configuration dictionary to query.
    key_path : str
        Key path in dot notation (e.g., "google_cloud.project_id").
    default : Any, optional
        Default value to return if key doesn't exist, by default None.

    Returns
    -------
    Any
        Configuration value if found, default value otherwise.

    Examples
    --------
    >>> config = {"google_cloud": {"project_id": "my-project"}}
    >>> get_config_value(config, "google_cloud.project_id")
    'my-project'
    >>> get_config_value(config, "nonexistent.key", "default")
    'default'
    """
    keys = key_path.split(".")
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


def set_config_value(config: dict, key_path: str, value: Any) -> None:
    """
    Set configuration value using dot notation path.

    Creates nested dictionaries as needed to set the value at the
    specified path.

    Parameters
    ----------
    config : dict
        Configuration dictionary to modify.
    key_path : str
        Key path in dot notation (e.g., "google_cloud.project_id").
    value : Any
        Value to set at the specified path.

    Examples
    --------
    >>> config = {}
    >>> set_config_value(config, "google_cloud.project_id", "my-project")
    >>> config
    {'google_cloud': {'project_id': 'my-project'}}
    """
    keys = key_path.split(".")
    current = config

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
