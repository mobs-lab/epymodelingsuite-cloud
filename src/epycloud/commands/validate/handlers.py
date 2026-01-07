"""Validate command handlers."""

import json
import os
from pathlib import Path
from typing import Any

import yaml

from epycloud.commands.validate.operations import (
    display_validation_results,
    validate_directory,
    validate_remote,
)
from epycloud.exceptions import ConfigError, ValidationError
from epycloud.lib.command_helpers import get_github_config, handle_dry_run, require_config
from epycloud.lib.output import error, info, warning
from epycloud.lib.validation import validate_exp_id, validate_github_token, validate_local_path


def handle(ctx: dict[str, Any]) -> int:
    """Handle validate command.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context

    Returns
    -------
    int
        Exit code (0=passed, 1=failed, 2=config error)
    """
    args = ctx["args"]
    verbose = ctx["verbose"]

    try:
        config = require_config(ctx)
    except ConfigError as e:
        error(str(e))
        return 2

    output_format = args.format

    # Validate inputs
    try:
        if args.exp_id:
            exp_id = validate_exp_id(args.exp_id)
        else:
            exp_id = None

        if args.path:
            local_path = validate_local_path(args.path, must_exist=True, must_be_dir=True)
        else:
            local_path = None

        if args.github_token:
            github_token = validate_github_token(args.github_token)
        else:
            github_token = None
    except ValidationError as e:
        error(str(e))
        return 1

    # Determine validation mode
    if local_path:
        info(f"Validating local config: {local_path}")
        print()

        if handle_dry_run(ctx, f"Validate local config at {local_path}"):
            return 0

        # Perform local validation
        try:
            result = validate_directory(
                config_dir=local_path,
                verbose=verbose,
            )

            # Output results
            if output_format == "json":
                print(json.dumps(result, indent=2))
            elif output_format == "yaml":
                print(yaml.dump(result, default_flow_style=False))
            else:
                display_validation_results(result)

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
        github = get_github_config(config)
        forecast_repo = github["forecast_repo"]

        if not forecast_repo:
            error("github.forecast_repo not configured")
            info("Set it in your profile or base config")
            return 2

        # Get GitHub token from multiple sources
        if not github_token:
            # Try config (merged from secrets.yaml)
            github = get_github_config(config)
            github_token = github["personal_access_token"]

        if not github_token:
            # Try environment variable
            github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")

        if handle_dry_run(
            ctx,
            f"Validate experiment '{exp_id}' from {forecast_repo}",
            {"repository": forecast_repo, "has_token": bool(github_token)},
        ):
            if not github_token:
                warning("GitHub token not found (required for actual validation)")
            return 0

        if not github_token:
            error("GitHub token not found")
            info("Provide via:")
            info("  --github-token TOKEN")
            info("  export GITHUB_TOKEN=github_pat_xxxxx (or ghp_xxxxx for classic)")
            info("  config secrets.yaml: github.personal_access_token")
            return 2

        info(f"Validating experiment: {exp_id}")
        info(f"Forecast repository: {forecast_repo}")
        print()

        # Perform remote validation
        try:
            result = validate_remote(
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
                display_validation_results(result)

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
