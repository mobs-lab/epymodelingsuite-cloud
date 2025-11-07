"""Validate command for validating experiment configuration."""

import argparse
import json
import os
import tempfile
import urllib.error
import urllib.request
from base64 import b64decode
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from epycloud.lib.output import error, info, success, warning


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the validate command parser.

    Args:
        subparsers: Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "validate",
        help="Validate experiment configuration",
        description="Validate experiment configuration using epymodelingsuite. "
        "Can validate from GitHub repository or local path.",
    )

    # Either exp-id (remote) or path (local) is required
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--exp-id",
        help="Experiment ID to validate from GitHub repository",
    )
    group.add_argument(
        "--path",
        type=Path,
        help="Path to local config directory (e.g., ./local/forecast/experiments/test-sim/config)",
    )

    parser.add_argument(
        "--format",
        choices=["text", "json", "yaml"],
        default="text",
        help="Output format: text|json|yaml (default: text)",
    )

    parser.add_argument(
        "--github-token",
        help="GitHub PAT for remote validation (or use from config/secrets/env)",
    )


def handle(ctx: Dict[str, Any]) -> int:
    """Handle validate command.

    Args:
        ctx: Command context

    Returns:
        Exit code (0=passed, 1=failed, 2=config error)
    """
    args = ctx["args"]
    config = ctx["config"]
    verbose = ctx["verbose"]
    dry_run = ctx["dry_run"]

    if not config:
        error("Configuration not loaded. Run 'epycloud config init' first")
        return 2

    exp_id = args.exp_id
    local_path = args.path
    output_format = args.format
    github_token = args.github_token

    # Determine validation mode
    if local_path:
        # Local path validation
        if not local_path.exists():
            error(f"Path does not exist: {local_path}")
            return 2

        if not local_path.is_dir():
            error(f"Path is not a directory: {local_path}")
            return 2

        info(f"Validating local config: {local_path}")
        print()

        if dry_run:
            info(f"Would validate local config at {local_path}")
            return 0

        # Perform local validation
        try:
            result = _validate_directory(
                config_dir=local_path,
                verbose=verbose,
            )

            # Output results
            if output_format == "json":
                print(json.dumps(result, indent=2))
            elif output_format == "yaml":
                print(yaml.dump(result, default_flow_style=False))
            else:
                _display_validation_results(result)

            # Return appropriate exit code
            if result.get("error"):
                return 1

            failed = sum(1 for cs in result.get("config_sets", []) if cs["status"] == "fail")
            return 1 if failed > 0 else 0

        except Exception as e:
            error(f"Validation failed: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            return 2

    else:
        # Remote (GitHub) validation
        # Get GitHub configuration
        github_config = config.get("github", {})
        forecast_repo = github_config.get("forecast_repo", "")

        if not forecast_repo:
            error("github.forecast_repo not configured")
            info("Set it in your profile or base config")
            return 2

        # Get GitHub token from multiple sources
        if not github_token:
            # Try secrets config
            secrets = config.get("secrets", {})
            github_token = secrets.get("github", {}).get("personal_access_token")

        if not github_token:
            # Try environment variable
            github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")

        if dry_run:
            info(f"Validating experiment: {exp_id}")
            info(f"Forecast repository: {forecast_repo}")
            info(f"Would validate experiment '{exp_id}' from {forecast_repo}")
            if not github_token:
                warning("GitHub token not found (required for actual validation)")
            return 0

        if not github_token:
            error("GitHub token not found")
            info("Provide via:")
            info("  --github-token TOKEN")
            info("  export GITHUB_TOKEN=ghp_xxxxx")
            info("  config secrets.yaml: github.personal_access_token")
            return 2

        info(f"Validating experiment: {exp_id}")
        info(f"Forecast repository: {forecast_repo}")
        print()

        # Perform remote validation
        try:
            result = _validate_remote(
                exp_id=exp_id,
                forecast_repo=forecast_repo,
                github_token=github_token,
                verbose=verbose,
            )

            # Output results
            if output_format == "json":
                print(json.dumps(result, indent=2))
            elif output_format == "yaml":
                print(yaml.dump(result, default_flow_style=False))
            else:
                _display_validation_results(result)

            # Return appropriate exit code
            if result.get("error"):
                return 1

            failed = sum(1 for cs in result.get("config_sets", []) if cs["status"] == "fail")
            return 1 if failed > 0 else 0

        except Exception as e:
            error(f"Validation failed: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            return 2


def _validate_directory(
    config_dir: Path,
    verbose: bool,
) -> Dict[str, Any]:
    """Validate all config sets in a directory.

    Args:
        config_dir: Path to config directory
        verbose: Verbose output

    Returns:
        Validation result dictionary
    """
    # Import epymodelingsuite utilities
    try:
        from epymodelingsuite.config_loader import (
            load_basemodel_config_from_file,
            load_calibration_config_from_file,
            load_output_config_from_file,
            load_sampling_config_from_file,
        )
        from epymodelingsuite.schema.general import validate_cross_config_consistency
        from epymodelingsuite.utils.config import identify_config_type
    except ImportError:
        return {
            "directory": str(config_dir),
            "config_sets": [],
            "error": "epymodelingsuite package not available"
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
            "error": "No YAML files found in directory"
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
            if verbose:
                warning(f"Could not classify {yaml_file.name}: {e}")

    if not basemodel_configs:
        return {
            "directory": str(config_dir),
            "config_sets": [],
            "error": "No basemodel configs found"
        }

    if not modelset_configs:
        return {
            "directory": str(config_dir),
            "config_sets": [],
            "error": "No modelset configs found"
        }

    # Validate the config set
    # Typically one experiment has: 1 basemodel + 1 modelset + optional output
    basemodel_path = basemodel_configs[0]
    modelset_path = modelset_configs[0]
    output_path = output_configs[0] if output_configs else None

    # Warn if multiple configs found
    if len(basemodel_configs) > 1 and verbose:
        warning(f"Multiple basemodel configs found, using: {basemodel_path.name}")
    if len(modelset_configs) > 1 and verbose:
        warning(f"Multiple modelset configs found, using: {modelset_path.name}")
    if len(output_configs) > 1 and verbose:
        warning(f"Multiple output configs found, using: {output_path.name}")

    success, error_msg = _validate_config_set(
        basemodel_path=basemodel_path,
        modelset_path=modelset_path,
        output_path=output_path,
        verbose=verbose,
    )

    set_result = {
        "basemodel": basemodel_path.name,
        "modelset": modelset_path.name,
        "status": "pass" if success else "fail"
    }

    if output_path is not None:
        set_result["output"] = output_path.name

    if error_msg:
        set_result["error"] = error_msg

    results = {
        "directory": str(config_dir),
        "config_sets": [set_result]
    }

    return results


def _validate_config_set(
    basemodel_path: Path,
    modelset_path: Path,
    output_path: Optional[Path],
    verbose: bool,
) -> tuple[bool, Optional[str]]:
    """Validate a set of configs.

    Args:
        basemodel_path: Path to basemodel config
        modelset_path: Path to modelset config
        output_path: Path to output config (optional)
        verbose: Verbose output

    Returns:
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


def _validate_remote(
    exp_id: str,
    forecast_repo: str,
    github_token: str,
    verbose: bool,
) -> Dict[str, Any]:
    """Validate remote experiment configuration from GitHub.

    Args:
        exp_id: Experiment ID
        forecast_repo: GitHub forecast repository (owner/repo)
        github_token: GitHub personal access token
        verbose: Verbose output

    Returns:
        Validation result dictionary
    """
    # Fetch config files from GitHub
    info("Fetching config files from GitHub...")
    try:
        config_files = _fetch_config_files(
            forecast_repo=forecast_repo,
            exp_id=exp_id,
            github_token=github_token,
            verbose=verbose,
        )
    except Exception as e:
        return {
            "directory": f"{forecast_repo}/experiments/{exp_id}/config",
            "config_sets": [],
            "error": f"Failed to fetch config files: {e}"
        }

    # Create temporary directory and write files
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write all files
            for filename, content in config_files.items():
                (tmppath / filename).write_text(content)

            # Validate the temporary directory
            result = _validate_directory(
                config_dir=tmppath,
                verbose=verbose,
            )

            # Update directory path to reflect remote source
            result["directory"] = f"{forecast_repo}/experiments/{exp_id}/config"

            return result

    except Exception as e:
        return {
            "directory": f"{forecast_repo}/experiments/{exp_id}/config",
            "config_sets": [],
            "error": str(e)
        }


def _fetch_config_files(
    forecast_repo: str,
    exp_id: str,
    github_token: str,
    verbose: bool,
) -> Dict[str, str]:
    """Fetch config files from GitHub repository.

    Args:
        forecast_repo: GitHub repository (owner/repo format)
        exp_id: Experiment ID
        github_token: GitHub personal access token
        verbose: Verbose output

    Returns:
        Dictionary mapping filename -> file content

    Raises:
        Exception: If files cannot be fetched
    """
    # Get list of files in the config directory
    config_dir_path = f"experiments/{exp_id}/config"
    api_url = f"https://api.github.com/repos/{forecast_repo}/contents/{config_dir_path}"

    if verbose:
        info(f"Fetching directory listing: {api_url}")

    try:
        req = urllib.request.Request(
            api_url,
            headers={
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        with urllib.request.urlopen(req) as response:
            files = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise Exception(f"Config directory not found: {config_dir_path}")
        else:
            raise Exception(f"GitHub API error {e.code}: {e.reason}")

    # Filter for YAML files
    yaml_files = [
        f for f in files
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
            content = _fetch_github_file(
                repo=forecast_repo,
                path=file_path,
                token=github_token,
                verbose=verbose,
            )
            config_files[filename] = content

        except Exception as e:
            if verbose:
                warning(f"Could not fetch {filename}: {e}")

    if not config_files:
        raise Exception(f"Failed to fetch any config files for experiment '{exp_id}'")

    return config_files


def _fetch_github_file(
    repo: str,
    path: str,
    token: str,
    verbose: bool,
) -> str:
    """Fetch a file from GitHub repository using API.

    Args:
        repo: Repository in owner/repo format
        path: File path in repository
        token: GitHub personal access token
        verbose: Verbose output

    Returns:
        File content as string

    Raises:
        Exception: If file cannot be fetched
    """
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"

    if verbose:
        info(f"Fetching: {path}")

    try:
        req = urllib.request.Request(
            api_url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))

            # GitHub API returns base64-encoded content
            if "content" in result:
                content = b64decode(result["content"]).decode("utf-8")
                return content
            else:
                raise Exception(f"No content field in API response for {path}")

    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise Exception(f"File not found: {path}")
        else:
            raise Exception(f"GitHub API error {e.code}: {e.reason}")


def _display_validation_results(result: Dict[str, Any]) -> None:
    """Display validation results in text format.

    Args:
        result: Validation result dictionary
    """
    print()
    print(f"Validating: {result['directory']}")
    print()

    # Check for directory-level errors
    if result.get("error"):
        error(result['error'])
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
