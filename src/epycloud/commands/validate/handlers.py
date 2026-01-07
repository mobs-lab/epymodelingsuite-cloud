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
from epycloud.lib.output import error, info, success, warning
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

    # Get GitHub token from multiple sources (for remote validation)
    github_token = None
    if args.github_token:
        try:
            github_token = validate_github_token(args.github_token)
        except ValidationError as e:
            error(str(e))
            return 1

    # Determine validation mode and get list of items to validate
    if args.path:
        # Local validation mode
        try:
            local_paths = [
                validate_local_path(p, must_exist=True, must_be_dir=True) for p in args.path
            ]
        except ValidationError as e:
            error(str(e))
            return 1

        # Handle single path with legacy output for json/yaml
        if len(local_paths) == 1 and output_format in ("json", "yaml"):
            return _validate_single_legacy(
                ctx, local_paths[0], output_format, verbose, is_local=True
            )

        # Table output for text format
        return _validate_multiple_local(ctx, local_paths, verbose)

    else:
        # Remote (GitHub) validation mode
        try:
            exp_ids = [validate_exp_id(eid) for eid in args.exp_id]
        except ValidationError as e:
            error(str(e))
            return 1

        # Get GitHub configuration
        github = get_github_config(config)
        forecast_repo = github["forecast_repo"]

        if not forecast_repo:
            error("github.forecast_repo not configured")
            info("Set it in your profile or base config")
            return 2

        # Get GitHub token
        if not github_token:
            github_token = github["personal_access_token"]

        if not github_token:
            github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")

        if not github_token:
            error("GitHub token not found")
            info("Provide via:")
            info("  --github-token TOKEN")
            info("  export GITHUB_TOKEN=github_pat_xxxxx (or ghp_xxxxx for classic)")
            info("  config secrets.yaml: github.personal_access_token")
            return 2

        # Handle dry-run
        if handle_dry_run(
            ctx,
            f"Validate {len(exp_ids)} experiment(s) from {forecast_repo}",
            {"repository": forecast_repo, "experiments": exp_ids},
        ):
            return 0

        # Handle single exp-id with legacy output for json/yaml
        if len(exp_ids) == 1 and output_format in ("json", "yaml"):
            return _validate_single_legacy(
                ctx, exp_ids[0], output_format, verbose,
                is_local=False, forecast_repo=forecast_repo, github_token=github_token
            )

        # Table output for text format
        return _validate_multiple_remote(
            ctx, exp_ids, forecast_repo, github_token, verbose
        )


def _validate_single_legacy(
    ctx: dict[str, Any],
    item: str | Path,
    output_format: str,
    verbose: bool,
    is_local: bool = False,
    forecast_repo: str = None,
    github_token: str = None,
) -> int:
    """Validate with legacy detailed output (for json/yaml formats)."""
    if is_local:
        print(f"Validating local config: {item}")
        print()

        if handle_dry_run(ctx, f"Validate local config at {item}"):
            return 0

        try:
            result = validate_directory(config_dir=item, verbose=verbose)
        except Exception as e:
            error(f"Validation failed: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            return 2
    else:
        print(f"Experiment: {item}")
        print(f"Repository: {forecast_repo}")
        print()

        try:
            result = validate_remote(
                exp_id=item,
                forecast_repo=forecast_repo,
                github_token=github_token,
                verbose=verbose,
            )
        except Exception as e:
            error(f"Validation failed: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            return 2

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


def _validate_multiple_local(
    ctx: dict[str, Any],
    local_paths: list[Path],
    verbose: bool,
) -> int:
    """Validate multiple local paths with pytest-style output."""
    import sys

    if handle_dry_run(ctx, f"Validate {len(local_paths)} local config(s)"):
        return 0

    print(f"Validating {len(local_paths)} local config(s)...")
    print()

    passed = 0
    failed = 0
    errored = 0

    # Color support check
    use_color = sys.stdout.isatty()

    for local_path in local_paths:
        try:
            result = validate_directory(
                config_dir=local_path,
                verbose=verbose,
            )

            # Extract config files
            config_files = _extract_config_files(result)

            # Check result
            if result.get("error"):
                error_text = result['error']
                # Distinguish between ERROR (not found) and FAILED (validation error)
                if "not found" in error_text.lower() or "epymodelingsuite" in error_text.lower():
                    status = "\033[33m[ERROR]\033[0m" if use_color else "[ERROR]"
                    print(f"{local_path} {status}")
                    print(f"  {error_text}")
                    errored += 1
                else:
                    status = "\033[31m[FAILED]\033[0m" if use_color else "[FAILED]"
                    print(f"{local_path} {status}")
                    print(f"  {error_text}")
                    failed += 1
            else:
                config_failed = sum(
                    1 for cs in result.get("config_sets", []) if cs["status"] == "fail"
                )
                if config_failed > 0:
                    status = "\033[31m[FAILED]\033[0m" if use_color else "[FAILED]"
                    print(f"{local_path} {status}")
                    if config_files:
                        print(f"  {config_files}")
                    errors = [cs.get("error", "") for cs in result.get("config_sets", [])
                              if cs["status"] == "fail" and "error" in cs]
                    for err in errors:
                        print(f"  {err}")
                    failed += 1
                else:
                    status = "\033[32m[PASSED]\033[0m" if use_color else "[PASSED]"
                    print(f"{local_path} {status}")
                    if config_files:
                        print(f"  {config_files}")
                    passed += 1

        except Exception as e:
            status = "\033[33m[ERROR]\033[0m" if use_color else "[ERROR]"
            print(f"{local_path} {status}")
            print(f"  {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            errored += 1

        print()

    # Print summary
    _print_summary(passed, failed, errored)

    return 0 if (failed == 0 and errored == 0) else 1


def _validate_multiple_remote(
    ctx: dict[str, Any],
    exp_ids: list[str],
    forecast_repo: str,
    github_token: str,
    verbose: bool,
) -> int:
    """Validate multiple remote experiments with pytest-style output."""
    import sys

    print(f"Repository: {forecast_repo}")
    print(f"Validating {len(exp_ids)} experiment(s)...")
    print()

    passed = 0
    failed = 0
    errored = 0

    # Color support check
    use_color = sys.stdout.isatty()

    for exp_id in exp_ids:
        try:
            result = validate_remote(
                exp_id=exp_id,
                forecast_repo=forecast_repo,
                github_token=github_token,
                verbose=verbose,
                quiet=True,
            )

            # Extract config files
            config_files = _extract_config_files(result)

            # Check result
            if result.get("error"):
                error_text = result['error']
                # Distinguish between ERROR (not found) and FAILED (validation error)
                if "not found" in error_text.lower() or "failed to fetch" in error_text.lower():
                    status = "\033[33m[ERROR]\033[0m" if use_color else "[ERROR]"
                    print(f"{exp_id} {status}")
                    print(f"  {error_text}")
                    errored += 1
                else:
                    status = "\033[31m[FAILED]\033[0m" if use_color else "[FAILED]"
                    print(f"{exp_id} {status}")
                    print(f"  {error_text}")
                    failed += 1
            else:
                config_failed = sum(
                    1 for cs in result.get("config_sets", []) if cs["status"] == "fail"
                )
                if config_failed > 0:
                    status = "\033[31m[FAILED]\033[0m" if use_color else "[FAILED]"
                    print(f"{exp_id} {status}")
                    if config_files:
                        print(f"  {config_files}")
                    errors = [cs.get("error", "") for cs in result.get("config_sets", [])
                              if cs["status"] == "fail" and "error" in cs]
                    for err in errors:
                        print(f"  {err}")
                    failed += 1
                else:
                    status = "\033[32m[PASSED]\033[0m" if use_color else "[PASSED]"
                    print(f"{exp_id} {status}")
                    if config_files:
                        print(f"  {config_files}")
                    passed += 1

        except Exception as e:
            status = "\033[33m[ERROR]\033[0m" if use_color else "[ERROR]"
            print(f"{exp_id} {status}")
            print(f"  {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            errored += 1

        print()

    # Print summary
    _print_summary(passed, failed, errored)

    return 0 if (failed == 0 and errored == 0) else 1


def _extract_config_files(result: dict[str, Any]) -> str:
    """Extract config file names from validation result."""
    config_sets = result.get("config_sets", [])
    if not config_sets:
        return ""

    cs = config_sets[0]
    files = [cs.get("basemodel", ""), cs.get("modelset", "")]
    if cs.get("output"):
        files.append(cs.get("output"))

    return " + ".join(f for f in files if f)


def _print_summary(passed: int, failed: int, errored: int) -> None:
    """Print validation summary in pytest style."""
    import sys

    total = passed + failed + errored
    parts = []

    if passed > 0:
        parts.append(f"{passed} passed")
    if failed > 0:
        parts.append(f"{failed} failed")
    if errored > 0:
        parts.append(f"{errored} error")

    summary = ", ".join(parts)

    if failed == 0 and errored == 0:
        symbol = "\033[32m✓\033[0m" if sys.stdout.isatty() else "✓"
        print(f"{symbol} {total} validated: {summary}")
    else:
        symbol = "\033[31m✗\033[0m" if sys.stdout.isatty() else "✗"
        print(f"{symbol} {total} validated: {summary}")
