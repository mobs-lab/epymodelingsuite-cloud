"""Handlers for download command."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from google.cloud import storage

from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import get_google_cloud_config, require_config
from epycloud.lib.output import (
    Colors,
    ask_confirmation,
    colorize,
    error,
    info,
    section_header,
    success,
    warning,
)

from .operations import (
    download_plots,
    filter_experiments,
    get_target_files,
    list_experiments,
    list_run_ids,
)


@dataclass
class DownloadItem:
    """A single experiment's download plan."""

    exp_path_rel: str
    exp_name: str
    run_id: str
    run_path: str
    num_runs: int = 1
    target_files: list[str] = field(default_factory=list)


def handle(ctx: dict[str, Any]) -> int:
    """Handle download command.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context

    Returns
    -------
    int
        Exit code
    """
    args = ctx["args"]
    verbose = ctx["verbose"]

    # Get config
    try:
        config = require_config(ctx)
        gcloud_config = get_google_cloud_config(ctx)
    except (ConfigError, KeyError) as e:
        error(str(e))
        return 2

    # Resolve bucket and dir_prefix (CLI overrides take precedence)
    bucket_name = args.bucket or gcloud_config["bucket_name"]
    pipeline_config = config.get("pipeline", {})
    dir_prefix = args.dir_prefix or pipeline_config.get("dir_prefix", "pipeline/flu/")

    # Ensure dir_prefix ends with /
    if not dir_prefix.endswith("/"):
        dir_prefix += "/"

    # Parse pattern: auto-append * if ends with /
    pattern = args.exp_filter
    if pattern.endswith("/"):
        pattern += "*"

    output_dir = Path(args.output_dir)
    name_format = args.name_format
    long_names = name_format == "long"
    nest_runs = args.nest_runs
    auto_confirm = args.yes

    if verbose:
        info(f"Bucket: {bucket_name}")
        info(f"Prefix: {dir_prefix}")
        info(f"Pattern: {pattern}")
        print()

    # Create GCS client
    try:
        client = storage.Client()
    except Exception as e:
        error(f"Failed to create GCS client: {e}")
        info("Ensure you are authenticated: gcloud auth application-default login")
        return 1

    # List all experiments under prefix
    try:
        all_experiments = list_experiments(client, bucket_name, dir_prefix)
    except Exception as e:
        error(f"Failed to list experiments: {e}")
        return 1

    if not all_experiments:
        warning(f"No experiments found under gs://{bucket_name}/{dir_prefix}")
        return 0

    # Filter experiments with pattern
    matched = filter_experiments(all_experiments, pattern)

    if not matched:
        warning(f"No experiments match pattern: {pattern}")
        if verbose:
            info(f"Available experiments ({len(all_experiments)}):")
            for exp in all_experiments[:20]:
                info(f"  {exp}")
            if len(all_experiments) > 20:
                info(f"  ... and {len(all_experiments) - 20} more")
        return 0

    # Pass 1: Build download plan (always auto-select latest run)
    plan: list[DownloadItem] = []
    plan_errors = 0

    for exp_path_rel in matched:
        exp_gcs_path = f"{dir_prefix}{exp_path_rel}"
        exp_name = exp_path_rel.rsplit("/", 1)[-1]
        target_files = get_target_files(exp_path_rel)

        # List run IDs
        try:
            run_ids = list_run_ids(client, bucket_name, exp_gcs_path)
        except Exception as e:
            error(f"  {exp_name}: failed to list runs: {e}")
            plan_errors += 1
            continue

        if not run_ids:
            if verbose:
                warning(f"  {exp_name}: no runs found")
            continue

        # Always select latest run (sorted lexicographically, YYYYMMDD-HHMMSS-*)
        selected_run_id = run_ids[-1]

        plan.append(
            DownloadItem(
                exp_path_rel=exp_path_rel,
                exp_name=exp_name,
                run_id=selected_run_id,
                run_path=f"{exp_gcs_path}/{selected_run_id}",
                num_runs=len(run_ids),
                target_files=target_files,
            )
        )

    if not plan:
        if plan_errors:
            error(f"Failed to build download plan ({plan_errors} error(s))")
            return 1
        warning("No experiments with runs found")
        return 0

    # Show confirmation screen
    total_files = sum(len(item.target_files) for item in plan)
    print()
    section_header("Download plan")
    info(f"{len(plan)} experiment(s), {total_files} file(s)")
    info(f"Output: {output_dir.resolve()}")
    info(f"Name format: {name_format}")
    print()

    for item in plan:
        exp_label = colorize(item.exp_path_rel, Colors.BOLD)
        run_label = colorize(item.run_id, Colors.CYAN)
        run_note = f"run_id: {run_label}"
        if item.num_runs > 1:
            multi = colorize(f"{item.num_runs} available, using latest", Colors.YELLOW)
            run_note += f", {multi}"
        print(f"  {exp_label}  ({run_note})")
        for f in item.target_files:
            print(f"    {colorize(f, Colors.DIM)}")

    print()

    if not auto_confirm:
        if not ask_confirmation("Proceed with download?", default=True):
            info("Cancelled")
            return 0

    # Pass 2: Execute downloads
    print()
    total_downloaded = 0
    total_skipped = 0
    total_errors = 0

    for item in plan:
        try:
            downloaded, skipped = download_plots(
                client=client,
                bucket_name=bucket_name,
                run_path=item.run_path,
                target_files=item.target_files,
                output_dir=output_dir,
                exp_name=item.exp_name,
                run_id=item.run_id,
                long_names=long_names,
                nest_runs=nest_runs,
                dir_prefix=dir_prefix,
            )
            total_downloaded += downloaded
            total_skipped += skipped

            parts = []
            if downloaded:
                parts.append(f"{downloaded} downloaded")
            if skipped:
                parts.append(f"{skipped} skipped (exists)")
            if not downloaded and not skipped:
                parts.append("no matching files")

            status_msg = ", ".join(parts)
            info(f"  {item.exp_name}: {status_msg}")

        except Exception as e:
            error(f"  {item.exp_name}: download failed: {e}")
            total_errors += 1

    # Summary
    print()
    if total_downloaded or total_skipped:
        summary_parts = []
        if total_downloaded:
            summary_parts.append(f"{total_downloaded} downloaded")
        if total_skipped:
            summary_parts.append(f"{total_skipped} skipped")
        if total_errors:
            summary_parts.append(f"{total_errors} errors")
        success(f"Done: {', '.join(summary_parts)}")
    elif total_errors:
        error(f"Failed with {total_errors} error(s)")
        return 1
    else:
        warning("No files found to download")

    return 0
