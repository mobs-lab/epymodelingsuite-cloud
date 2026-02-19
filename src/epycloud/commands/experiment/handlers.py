"""Handler functions for experiment subcommands."""

from datetime import UTC, datetime
from fnmatch import fnmatch
from typing import Any

from google.cloud import storage

from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import get_google_cloud_config, require_config
from epycloud.lib.formatters import format_table
from epycloud.lib.gcs import (
    extract_scan_prefix,
    list_experiment_runs,
    normalize_filter_patterns,
    parse_run_id_datetime,
)
from epycloud.lib.output import error, status, warning


def handle(ctx: dict[str, Any]) -> int:
    """Handle experiment command.

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

    # Validate configuration
    try:
        require_config(ctx)
    except ConfigError as e:
        error(str(e))
        return 2

    if not args.experiment_subcommand:
        if hasattr(args, "_experiment_parser"):
            args._experiment_parser.print_help()
        else:
            error("No subcommand specified. Use 'epycloud experiment --help'")
        return 1

    if args.experiment_subcommand == "list":
        return handle_list(ctx)
    else:
        error(f"Unknown subcommand: {args.experiment_subcommand}")
        return 1


def handle_list(ctx: dict[str, Any]) -> int:
    """Handle experiment list command.

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
    config = ctx["config"]
    verbose = ctx["verbose"]

    # Resolve bucket and dir_prefix (CLI overrides take precedence)
    try:
        gcloud_config = get_google_cloud_config(ctx)
    except (ConfigError, KeyError) as e:
        error(str(e))
        return 2

    bucket_name = args.bucket or gcloud_config["bucket_name"]
    pipeline_config = config.get("pipeline", {})
    dir_prefix = args.dir_prefix or pipeline_config.get("dir_prefix", "pipeline/flu/")

    if not dir_prefix.endswith("/"):
        dir_prefix += "/"

    # Resolve filter patterns and scan prefix
    raw_pattern = args.exp_filter
    if raw_pattern:
        patterns = normalize_filter_patterns(raw_pattern)
        scan_prefix = extract_scan_prefix(patterns)
    else:
        patterns = None
        scan_prefix = ""

    if verbose:
        status(f"Bucket: {bucket_name}")
        status(f"Prefix: {dir_prefix}")
        if raw_pattern:
            status(f"Filter: {raw_pattern}")
        status("")

    # Create GCS client
    try:
        client = storage.Client()
    except Exception as e:
        error(f"Failed to create GCS client: {e}")
        status("Ensure you are authenticated: gcloud auth application-default login")
        return 1

    # List all (experiment, run_id) pairs in a single flat scan
    if raw_pattern:
        status(f"Searching for experiments matching '{raw_pattern}'...")
    else:
        status("Searching for experiments...")
    try:
        all_runs = list_experiment_runs(
            client, bucket_name, dir_prefix, scan_prefix=scan_prefix
        )
    except Exception as e:
        error(f"Failed to list experiments: {e}")
        return 1

    if not all_runs:
        warning(f"No experiments found under gs://{bucket_name}/{dir_prefix}")
        return 0

    # Apply filter if provided
    if patterns:
        all_runs = [
            (exp, run_id)
            for exp, run_id in all_runs
            if any(fnmatch(exp, p) for p in patterns)
        ]
        if not all_runs:
            warning(f"No experiments match pattern: {raw_pattern}")
            return 0

    # Count runs per experiment
    runs_per_exp: dict[str, int] = {}
    for exp, _ in all_runs:
        runs_per_exp[exp] = runs_per_exp.get(exp, 0) + 1

    unique_experiments = len(runs_per_exp)
    total_runs = len(all_runs)

    # If --latest, keep only the last run_id per experiment
    if args.latest:
        latest: dict[str, str] = {}
        for exp, run_id in all_runs:
            if exp not in latest or run_id > latest[exp]:
                latest[exp] = run_id
        all_runs = [(exp, run_id) for exp, run_id in sorted(latest.items())]

    # Sort by run_id descending (most recent first)
    all_runs.sort(key=lambda r: r[1], reverse=True)

    # Apply limit (0 = no limit)
    truncated = False
    if args.limit and len(all_runs) > args.limit:
        all_runs = all_runs[: args.limit]
        truncated = True

    has_multi = any(c > 1 for c in runs_per_exp.values())
    status(f"Found {unique_experiments} experiment(s), {total_runs} run(s)")
    if has_multi:
        status("* experiment has multiple runs, use --latest to show only the most recent")

    # Output
    if args.output_format == "uri":
        for exp, run_id in all_runs:
            print(f"gs://{bucket_name}/{dir_prefix}{exp}/{run_id}/")
        return 0

    # Table format
    # Get local timezone abbreviation for header
    tz_abbr = datetime.now(UTC).astimezone().strftime("%Z")

    table_rows: list[list[str]] = []
    for exp, run_id in all_runs:
        dt = parse_run_id_datetime(run_id)
        if dt:
            # Convert to local time for display
            local_dt = dt.replace(tzinfo=UTC).astimezone()
            timestamp_str = local_dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestamp_str = ""
        count = runs_per_exp.get(exp, 1)
        table_rows.append([timestamp_str, exp, run_id, "*" if count > 1 else ""])

    headers = [f"TIMESTAMP ({tz_abbr})", "EXPERIMENT ID", "RUN ID", ""]
    print()
    print(format_table(headers, table_rows))

    if truncated:
        print()
        status(f"Showing {len(table_rows)} of {total_runs} run(s), use -n 0 to show all")

    print()
    return 0
