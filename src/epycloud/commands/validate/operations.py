"""Validate operations and utilities."""

import fnmatch
import tempfile
from base64 import b64decode
from pathlib import Path
from typing import Any

import requests

from epycloud.lib.output import error, info, success, warning


def validate_directory(
    config_dir: Path,
    verbose: bool,
    quiet: bool = False,
) -> dict[str, Any]:
    """Validate all config sets in a directory.

    Parameters
    ----------
    config_dir : Path
        Path to config directory
    verbose : bool
        Verbose output
    quiet : bool, optional
        Suppress progress messages (default: False)

    Returns
    -------
    dict[str, Any]
        Validation result dictionary
    """
    # Import epymodelingsuite utilities
    try:
        from epymodelingsuite.utils.config import identify_config_type
    except ImportError:
        return {
            "directory": str(config_dir),
            "config_sets": [],
            "error": "epymodelingsuite package not available",
        }

    # Find all YAML files
    yaml_files = []
    for ext in ["*.yml", "*.yaml"]:
        yaml_files.extend(config_dir.glob(ext))
    yaml_files = sorted(yaml_files)

    if not yaml_files:
        return {
            "directory": str(config_dir),
            "config_sets": [],
            "error": "No YAML files found in directory",
        }

    # Classify configs
    basemodel_configs = []
    modelset_configs = []
    output_configs = []

    for yaml_file in yaml_files:
        try:
            config_type = identify_config_type(str(yaml_file))
            if config_type == "basemodel":
                basemodel_configs.append(yaml_file)
            elif config_type in ["sampling", "calibration"]:
                modelset_configs.append(yaml_file)
            elif config_type == "output":
                output_configs.append(yaml_file)
        except Exception as e:
            if verbose and not quiet:
                warning(f"Could not classify {yaml_file.name}: {e}")

    if not basemodel_configs:
        return {
            "directory": str(config_dir),
            "config_sets": [],
            "error": "No basemodel configs found",
        }

    if not modelset_configs:
        return {
            "directory": str(config_dir),
            "config_sets": [],
            "error": "No modelset configs found",
        }

    # Validate all config sets (all combinations of basemodel × modelset × output)
    results = {
        "directory": str(config_dir),
        "config_sets": []
    }

    # If no output configs, validate basemodel-modelset only
    output_paths = output_configs if output_configs else [None]

    for basemodel_path in basemodel_configs:
        for modelset_path in modelset_configs:
            for output_path in output_paths:
                success_val, error_msg = validate_config_set(
                    basemodel_path=basemodel_path,
                    modelset_path=modelset_path,
                    output_path=output_path,
                    verbose=verbose,
                )

                set_result = {
                    "basemodel": basemodel_path.name,
                    "modelset": modelset_path.name,
                    "status": "pass" if success_val else "fail",
                }

                if output_path is not None:
                    set_result["output"] = output_path.name

                if error_msg:
                    set_result["error"] = error_msg

                results["config_sets"].append(set_result)

    return results


def validate_config_set(
    basemodel_path: Path,
    modelset_path: Path,
    output_path: Path | None,
    verbose: bool,
) -> tuple[bool, str | None]:
    """Validate a set of configs.

    Parameters
    ----------
    basemodel_path : Path
        Path to basemodel config
    modelset_path : Path
        Path to modelset config
    output_path : Path | None
        Path to output config (optional)
    verbose : bool
        Verbose output

    Returns
    -------
    tuple[bool, str | None]
        Tuple of (success, error_message)
    """
    try:
        from epymodelingsuite.config_loader import (
            load_basemodel_config_from_file,
            load_calibration_config_from_file,
            load_output_config_from_file,
            load_sampling_config_from_file,
        )
        from epymodelingsuite.schema.general import validate_cross_config_consistency
        from epymodelingsuite.utils.config import identify_config_type

        # Identify config types
        basemodel_type = identify_config_type(str(basemodel_path))
        modelset_type = identify_config_type(str(modelset_path))

        if basemodel_type != "basemodel":
            return False, f"Expected basemodel config, got: {basemodel_type}"

        if modelset_type not in ["sampling", "calibration"]:
            return False, f"Expected sampling or calibration config, got: {modelset_type}"

        # Load configs
        basemodel_config = load_basemodel_config_from_file(str(basemodel_path))

        if modelset_type == "sampling":
            modelset_config = load_sampling_config_from_file(str(modelset_path))
        else:  # calibration
            modelset_config = load_calibration_config_from_file(str(modelset_path))

        # Load output config if provided
        output_config = None
        if output_path is not None:
            output_type = identify_config_type(str(output_path))
            if output_type != "output":
                return False, f"Expected output config, got: {output_type}"
            output_config = load_output_config_from_file(str(output_path))

        # Validate consistency
        validate_cross_config_consistency(basemodel_config, modelset_config, output_config)

        return True, None

    except Exception as e:
        return False, str(e)


def validate_remote(
    exp_id: str,
    forecast_repo: str,
    github_token: str,
    verbose: bool,
    quiet: bool = False,
) -> dict[str, Any]:
    """Validate remote experiment configuration from GitHub.

    Parameters
    ----------
    exp_id : str
        Experiment ID
    forecast_repo : str
        GitHub forecast repository (owner/repo)
    github_token : str
        GitHub personal access token
    verbose : bool
        Verbose output
    quiet : bool, optional
        Suppress progress messages (default: False)

    Returns
    -------
    dict[str, Any]
        Validation result dictionary
    """
    # Fetch config files from GitHub
    if not quiet:
        print("Fetching config files from GitHub...")
    try:
        config_files = fetch_config_files(
            forecast_repo=forecast_repo,
            exp_id=exp_id,
            github_token=github_token,
            verbose=verbose,
            quiet=quiet,
        )
    except Exception as e:
        return {
            "directory": f"{forecast_repo}/experiments/{exp_id}/config",
            "config_sets": [],
            "error": f"Failed to fetch config files: {e}",
        }

    # Create temporary directory and write files
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write all files
            for filename, content in config_files.items():
                (tmppath / filename).write_text(content)

            # Validate the temporary directory
            result = validate_directory(
                config_dir=tmppath,
                verbose=verbose,
                quiet=quiet,
            )

            # Update directory path to reflect remote source
            result["directory"] = f"{forecast_repo}/experiments/{exp_id}/config"

            return result

    except Exception as e:
        return {
            "directory": f"{forecast_repo}/experiments/{exp_id}/config",
            "config_sets": [],
            "error": str(e),
        }


def fetch_config_files(
    forecast_repo: str,
    exp_id: str,
    github_token: str,
    verbose: bool,
    quiet: bool = False,
) -> dict[str, str]:
    """Fetch config files from GitHub repository.

    Parameters
    ----------
    forecast_repo : str
        GitHub repository (owner/repo format)
    exp_id : str
        Experiment ID
    github_token : str
        GitHub personal access token
    verbose : bool
        Verbose output
    quiet : bool, optional
        Suppress progress messages (default: False)

    Returns
    -------
    dict[str, str]
        Dictionary mapping filename -> file content

    Raises
    ------
    Exception
        If files cannot be fetched
    """
    # Get list of files in the config directory
    config_dir_path = f"experiments/{exp_id}/config"
    api_url = f"https://api.github.com/repos/{forecast_repo}/contents/{config_dir_path}"

    if verbose and not quiet:
        info(f"Fetching directory listing: {api_url}")

    try:
        response = requests.get(
            api_url,
            headers={
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        response.raise_for_status()
        files = response.json()

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise Exception(f"Config directory not found: {config_dir_path}")
        else:
            status_code = e.response.status_code if e.response else "unknown"
            raise Exception(f"GitHub API error {status_code}")

    # Filter for YAML files
    yaml_files = [
        f
        for f in files
        if f.get("type") == "file" and f.get("name", "").endswith((".yaml", ".yml"))
    ]

    if not yaml_files:
        raise Exception(f"No YAML files found in {config_dir_path}")

    # Fetch each YAML file
    config_files = {}
    for file_info in yaml_files:
        filename = file_info.get("name")
        file_path = f"experiments/{exp_id}/config/{filename}"

        try:
            content = fetch_github_file(
                repo=forecast_repo,
                path=file_path,
                token=github_token,
                verbose=verbose,
                quiet=quiet,
            )
            config_files[filename] = content

        except Exception as e:
            if verbose and not quiet:
                warning(f"Could not fetch {filename}: {e}")

    if not config_files:
        raise Exception(f"Failed to fetch any config files for experiment '{exp_id}'")

    return config_files


def fetch_github_file(
    repo: str,
    path: str,
    token: str,
    verbose: bool,
    quiet: bool = False,
) -> str:
    """Fetch a file from GitHub repository using API.

    Parameters
    ----------
    repo : str
        Repository in owner/repo format
    path : str
        File path in repository
    token : str
        GitHub personal access token
    verbose : bool
        Verbose output
    quiet : bool, optional
        Suppress progress messages (default: False)

    Returns
    -------
    str
        File content as string

    Raises
    ------
    Exception
        If file cannot be fetched
    """
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"

    if verbose and not quiet:
        info(f"Fetching: {path}")

    try:
        response = requests.get(
            api_url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        response.raise_for_status()
        result = response.json()

        # GitHub API returns base64-encoded content
        if "content" in result:
            content = b64decode(result["content"]).decode("utf-8")
            return content
        else:
            raise Exception(f"No content field in API response for {path}")

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise Exception(f"File not found: {path}")
        else:
            status_code = e.response.status_code if e.response else "unknown"
            raise Exception(f"GitHub API error {status_code}")


def expand_exp_id_pattern(
    pattern: str,
    forecast_repo: str,
    github_token: str,
    verbose: bool = False,
) -> list[str]:
    """Expand exp-id pattern to list of matching experiment IDs.

    Supports glob patterns like:
    - 202549/* (all experiments in directory)
    - test-* (all experiments starting with "test-")
    - */calibration (all "calibration" experiments in subdirectories)

    Parameters
    ----------
    pattern : str
        Experiment ID pattern (supports *, ?, [])
    forecast_repo : str
        GitHub forecast repository (owner/repo)
    github_token : str
        GitHub personal access token
    verbose : bool, optional
        Verbose output (default: False)

    Returns
    -------
    list[str]
        List of matching experiment IDs

    Raises
    ------
    Exception
        If pattern expansion fails
    """
    # Check if pattern contains wildcards
    if not any(c in pattern for c in ['*', '?', '[']):
        # No wildcards, return as-is
        return [pattern]

    # Split pattern into directory levels
    pattern_parts = pattern.split('/')

    # Fetch experiments directory listing
    api_url = f"https://api.github.com/repos/{forecast_repo}/contents/experiments"

    if verbose:
        info(f"Fetching experiments from: {api_url}")

    try:
        response = requests.get(
            api_url,
            headers={
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        response.raise_for_status()
        items = response.json()

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise Exception(f"Experiments directory not found in {forecast_repo}")
        else:
            status_code = e.response.status_code if e.response else "unknown"
            raise Exception(f"GitHub API error {status_code}")

    # Filter directories
    directories = [item["name"] for item in items if item.get("type") == "dir"]

    # Handle different pattern scenarios
    if len(pattern_parts) == 1:
        # Simple pattern like "test-*"
        matches = fnmatch.filter(directories, pattern_parts[0])
    else:
        # Multi-level pattern like "202549/*" or "*/calibration"
        # For now, we'll handle the common case of "prefix/*"
        if pattern_parts[1] == '*':
            # Match first level, then fetch subdirectories
            first_level_matches = fnmatch.filter(directories, pattern_parts[0])
            matches = []
            for first_level in first_level_matches:
                # Fetch subdirectories
                sub_api_url = f"https://api.github.com/repos/{forecast_repo}/contents/experiments/{first_level}"
                try:
                    sub_response = requests.get(
                        sub_api_url,
                        headers={
                            "Authorization": f"token {github_token}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                    )
                    sub_response.raise_for_status()
                    sub_items = sub_response.json()
                    sub_dirs = [
                        item["name"] for item in sub_items
                        if item.get("type") == "dir" and "config" in item["name"].lower() or item.get("type") == "dir"
                    ]
                    # Check if it's a valid experiment (has config directory)
                    if any("config" in item["name"].lower() for item in sub_items if item.get("type") == "dir"):
                        # This is likely an experiment directory with config subdirectory
                        matches.append(first_level)
                    else:
                        # These might be experiment subdirectories
                        for sub_dir in sub_dirs:
                            matches.append(f"{first_level}/{sub_dir}")
                except Exception as e:
                    if verbose:
                        warning(f"Could not fetch subdirectories for {first_level}: {e}")
        else:
            # General multi-level pattern matching
            matches = []
            for directory in directories:
                if len(pattern_parts) == 2:
                    # Two-level pattern
                    exp_id = directory
                    if fnmatch.fnmatch(exp_id, pattern_parts[0]):
                        # Check subdirectories
                        sub_api_url = f"https://api.github.com/repos/{forecast_repo}/contents/experiments/{directory}"
                        try:
                            sub_response = requests.get(
                                sub_api_url,
                                headers={
                                    "Authorization": f"token {github_token}",
                                    "Accept": "application/vnd.github.v3+json",
                                },
                            )
                            sub_response.raise_for_status()
                            sub_items = sub_response.json()
                            sub_dirs = [item["name"] for item in sub_items if item.get("type") == "dir"]
                            for sub_dir in fnmatch.filter(sub_dirs, pattern_parts[1]):
                                matches.append(f"{directory}/{sub_dir}")
                        except Exception:
                            pass

    if not matches:
        raise Exception(f"No experiments match pattern: {pattern}")

    if verbose:
        info(f"Pattern '{pattern}' expanded to {len(matches)} experiment(s)")

    return sorted(matches)


def display_validation_results(result: dict[str, Any]) -> None:
    """Display validation results in text format.

    Parameters
    ----------
    result : dict[str, Any]
        Validation result dictionary
    """
    print(f"Validating: {result['directory']}")
    print()

    # Check for directory-level errors
    if result.get("error"):
        error(result["error"])
        return

    config_sets = result.get("config_sets", [])
    if not config_sets:
        info("No config sets found")
        return

    # Display config set (typically just one)
    config_set = config_sets[0]
    status = config_set["status"]
    basemodel = config_set["basemodel"]
    modelset = config_set["modelset"]
    output = config_set.get("output")

    config_desc = f"{basemodel} + {modelset}"
    if output:
        config_desc += f" + {output}"

    if status == "pass":
        success(f"Validation passed: {config_desc}")
        print()
    else:
        error(f"Validation failed: {config_desc}")
        if "error" in config_set:
            print(f"  {config_set['error']}")
        print()
