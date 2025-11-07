"""Configuration loader with environment and profile support."""

import os
from pathlib import Path
from typing import Any, Optional

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
    """Load and merge configuration from multiple sources."""

    def __init__(
        self,
        environment: str = "dev",
        profile: Optional[str] = None,
        config_path: Optional[Path] = None,
    ):
        """Initialize config loader.

        Args:
            environment: Environment name (dev, prod, local)
            profile: Profile name (flu, covid, rsv, etc.) - if None, uses active profile
            config_path: Optional path to base config file (overrides default)
        """
        self.environment = environment
        self.profile = profile or self._get_active_profile()
        self.config_path = config_path or get_config_file()

    def _get_active_profile(self) -> Optional[str]:
        """Get the currently active profile.

        Returns:
            Active profile name or None
        """
        active_profile_file = get_active_profile_file()
        if active_profile_file.exists():
            return active_profile_file.read_text().strip()
        return None

    def _load_yaml_file(self, path: Path) -> dict:
        """Load YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML content or empty dict if file doesn't exist
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
        """Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _interpolate_templates(self, config: dict) -> dict:
        """Interpolate template variables in config.

        Replaces {environment} and {profile} placeholders.

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with interpolated values
        """
        def interpolate_value(value: Any) -> Any:
            if isinstance(value, str):
                value = value.replace("{environment}", self.environment)
                if self.profile:
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
        """Apply environment variable overrides.

        Environment variables in format: EPYCLOUD_SECTION_SUBSECTION_KEY

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with environment variable overrides
        """
        prefix = "EPYCLOUD_"

        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue

            # Parse key path
            key_path = env_key[len(prefix):].lower().split("_")

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
        """Load and merge configuration from all sources.

        Merge order (lowest to highest priority):
        1. Base config (config.yaml)
        2. Environment config (environments/{env}.yaml)
        3. Profile config (profiles/{profile}.yaml)
        4. Project config (./epycloud.yaml)
        5. Secrets (secrets.yaml)
        6. Environment variables (EPYCLOUD_*)

        Returns:
            Merged configuration dictionary
        """
        # Start with empty config
        config = {}

        # 1. Load base config
        config = self._deep_merge(config, self._load_yaml_file(self.config_path))

        # 2. Load environment config
        env_file = get_environment_file(self.environment)
        config = self._deep_merge(config, self._load_yaml_file(env_file))

        # 3. Load profile config
        if self.profile:
            profile_file = get_profile_file(self.profile)
            config = self._deep_merge(config, self._load_yaml_file(profile_file))

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
            "profile": self.profile,
            "config_sources": self._get_loaded_sources(),
        }

        return config

    def _get_loaded_sources(self) -> list[str]:
        """Get list of config files that were loaded.

        Returns:
            List of config file paths that exist and were loaded
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
    """Get config value using dot notation.

    Args:
        config: Configuration dictionary
        key_path: Key path in dot notation (e.g., "google_cloud.project_id")
        default: Default value if key doesn't exist

    Returns:
        Config value or default
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
    """Set config value using dot notation.

    Args:
        config: Configuration dictionary
        key_path: Key path in dot notation (e.g., "google_cloud.project_id")
        value: Value to set
    """
    keys = key_path.split(".")
    current = config

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
