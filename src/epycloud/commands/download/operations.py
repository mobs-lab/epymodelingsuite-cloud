"""GCS listing and downloading operations for download command."""

from pathlib import Path

from google.cloud import storage

# Re-export shared GCS operations for backward compatibility
from epycloud.lib.gcs import (
    _RUN_ID_RE,
    filter_experiments,
    list_experiments,
    list_run_ids,
)

__all__ = [
    "_RUN_ID_RE",
    "build_local_filename",
    "download_plots",
    "filter_experiments",
    "find_matching_blobs",
    "get_target_files",
    "list_experiments",
    "list_run_ids",
]


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
        Experiment name or relative path (used for subdirectory)
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
