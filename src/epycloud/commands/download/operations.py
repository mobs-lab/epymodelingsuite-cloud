"""GCS listing and downloading operations for download command."""

from fnmatch import fnmatch
from pathlib import Path

from google.cloud import storage


def list_experiments(
    client: storage.Client,
    bucket_name: str,
    prefix: str,
) -> list[str]:
    """List experiment directories under a GCS prefix.

    The storage layout is {prefix}{week}/{exp_name}/{run_id}/..., so this
    lists two levels deep and returns paths like "{week}/{exp_name}".

    Parameters
    ----------
    client : storage.Client
        GCS client
    bucket_name : str
        GCS bucket name
    prefix : str
        GCS prefix to list under (e.g. "pipeline/flu/")

    Returns
    -------
    list[str]
        List of experiment paths relative to prefix (e.g. "202605/ed_smc_rmse_...")
    """
    bucket = client.bucket(bucket_name)

    # First level: week directories
    blobs = bucket.list_blobs(prefix=prefix, delimiter="/")
    for _ in blobs:
        pass
    week_prefixes = list(blobs.prefixes)

    # Second level: experiment directories under each week
    experiments = []
    for week_prefix in week_prefixes:
        week_name = week_prefix[len(prefix) :].rstrip("/")
        blobs = bucket.list_blobs(prefix=week_prefix, delimiter="/")
        for _ in blobs:
            pass
        for exp_prefix in blobs.prefixes:
            exp_name = exp_prefix[len(week_prefix) :].rstrip("/")
            if exp_name:
                experiments.append(f"{week_name}/{exp_name}")

    return sorted(experiments)


def list_run_ids(
    client: storage.Client,
    bucket_name: str,
    exp_path: str,
) -> list[str]:
    """List run_id directories under an experiment path.

    Parameters
    ----------
    client : storage.Client
        GCS client
    bucket_name : str
        GCS bucket name
    exp_path : str
        Full experiment path (e.g. "pipeline/flu/202606/ed_smc_rmse_...")

    Returns
    -------
    list[str]
        List of run_id directory names, sorted lexicographically
    """
    bucket = client.bucket(bucket_name)
    prefix = exp_path if exp_path.endswith("/") else exp_path + "/"
    blobs = bucket.list_blobs(prefix=prefix, delimiter="/")

    for _ in blobs:
        pass

    run_ids = []
    for run_prefix in blobs.prefixes:
        run_id = run_prefix[len(prefix) :].rstrip("/")
        if run_id:
            run_ids.append(run_id)

    return sorted(run_ids)


def get_target_files(exp_path: str) -> list[str]:
    """Determine which files to download based on experiment name prefix.

    Parameters
    ----------
    exp_path : str
        Experiment path, possibly including week prefix
        (e.g. "202605/ed_smc_rmse_202552-202605_noschool" or just "ed_smc_rmse_...")

    Returns
    -------
    list[str]
        List of target filenames to download
    """
    # Extract just the experiment name (last component)
    exp_name = exp_path.rsplit("/", 1)[-1]

    base_files = [
        "posterior_grid.pdf",
        "quantiles_grid_sidebyside.pdf",
    ]

    if exp_name.startswith("hosp_"):
        return base_files + ["categorical_rate_trends.pdf"]

    return base_files


def filter_experiments(experiments: list[str], pattern: str) -> list[str]:
    """Filter experiment names using fnmatch pattern.

    Parameters
    ----------
    experiments : list[str]
        List of experiment names
    pattern : str
        Glob pattern (fnmatch-compatible)

    Returns
    -------
    list[str]
        Filtered list of experiment names matching the pattern
    """
    return [exp for exp in experiments if fnmatch(exp, pattern)]


def find_matching_blobs(
    client: storage.Client,
    bucket_name: str,
    run_path: str,
    target_files: list[str],
) -> list[storage.Blob]:
    """Find blobs matching target filenames under a run's outputs/ directory.

    Searches all outputs/ subdirectories (timestamped) for matching files.

    Parameters
    ----------
    client : storage.Client
        GCS client
    bucket_name : str
        GCS bucket name
    run_path : str
        Full run path (e.g. "pipeline/flu/202606/exp_name/run_id")
    target_files : list[str]
        List of filenames to match

    Returns
    -------
    list[storage.Blob]
        List of matching blobs
    """
    bucket = client.bucket(bucket_name)
    outputs_prefix = run_path.rstrip("/") + "/outputs/"
    blobs = bucket.list_blobs(prefix=outputs_prefix)

    matching = []
    for blob in blobs:
        blob_filename = blob.name.rsplit("/", 1)[-1]
        if blob_filename in target_files:
            matching.append(blob)

    return matching


def build_local_filename(
    blob: storage.Blob,
    long_names: bool,
    dir_prefix: str = "",
) -> str:
    """Build the local filename for a downloaded blob.

    Parameters
    ----------
    blob : storage.Blob
        GCS blob
    long_names : bool
        If True, flatten the GCS path into the filename using underscores
    dir_prefix : str
        GCS dir prefix to strip from long names (e.g. "pipeline/flu/")

    Returns
    -------
    str
        Local filename
    """
    name = blob.name or ""
    if long_names:
        # Strip dir_prefix before flattening
        if dir_prefix and name.startswith(dir_prefix):
            name = name[len(dir_prefix):]
        # Flatten remaining path: replace / with _
        return name.replace("/", "_")

    # Short name: just the filename
    return name.rsplit("/", 1)[-1]


def download_plots(
    client: storage.Client,
    bucket_name: str,
    run_path: str,
    target_files: list[str],
    output_dir: Path,
    exp_name: str,
    run_id: str | None,
    long_names: bool,
    nest_runs: bool,
    dir_prefix: str = "",
) -> tuple[int, int]:
    """Find and download matching output files from a run.

    Parameters
    ----------
    client : storage.Client
        GCS client
    bucket_name : str
        GCS bucket name
    run_path : str
        Full run path in GCS
    target_files : list[str]
        List of target filenames to download
    output_dir : Path
        Base output directory
    exp_name : str
        Experiment name (used for subdirectory)
    run_id : str or None
        Run ID (used for subdirectory when nest_runs is True)
    long_names : bool
        Use flattened GCS-style filenames
    nest_runs : bool
        Add run_id subdirectory under experiment
    dir_prefix : str
        GCS dir prefix to strip from long names

    Returns
    -------
    tuple[int, int]
        Count of (downloaded, skipped) files
    """
    matching_blobs = find_matching_blobs(client, bucket_name, run_path, target_files)

    # Build local directory path
    local_dir = output_dir / exp_name
    if nest_runs and run_id:
        local_dir = local_dir / run_id
    local_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0

    for blob in matching_blobs:
        filename = build_local_filename(blob, long_names, dir_prefix)
        local_path = local_dir / filename

        if local_path.exists():
            skipped += 1
            continue

        blob.download_to_filename(str(local_path))
        downloaded += 1

    return downloaded, skipped
