"""
Storage abstraction layer for switching between GCS and local filesystem.

Supports two execution modes via EXECUTION_MODE environment variable:
- 'cloud': Uses Google Cloud Storage API
- 'local': Uses filesystem operations at /data/bucket/ mount

The storage layer automatically constructs paths based on configuration:
- In local mode: /data/bucket/{path}
- In cloud mode: gs://{GCS_BUCKET}/{path}

Usage:
    from util.storage import load_bytes, save_bytes, get_path

    # Build a path
    input_path = get_path("builder-artifacts", "input_0000.pkl")

    # Load/save works in both modes
    data = load_bytes(input_path)
    save_bytes(output_path, data)
"""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from epymodelingsuite.telemetry import ExecutionTelemetry

# Module-level logger for utility logging
# Use standard logging.getLogger for utility modules (not setup_logger)
_logger = logging.getLogger(__name__)

# Storage logger for verbose I/O operations
from util.logger import StorageLogger

_storage_logger = StorageLogger(_logger)

# GCS client cache for cloud mode (optimization)
_gcs_client = None


def _get_execution_mode() -> str:
    """Get the execution mode from environment variable."""
    return os.getenv("EXECUTION_MODE", "cloud").lower()


def _get_local_base_path() -> Path:
    """Get the base path for local storage."""
    return Path(os.getenv("LOCAL_DATA_PATH", "/data"))


def _get_gcs_client():
    """Get or create cached GCS client.

    Returns a cached google.cloud.storage.Client instance to avoid
    creating new clients on every operation. This improves performance
    for high-frequency operations.

    Returns
    -------
    google.cloud.storage.Client
        Cached GCS client instance
    """
    global _gcs_client
    if _gcs_client is None:
        from google.cloud import storage

        _gcs_client = storage.Client()
    return _gcs_client


def get_config() -> dict:
    """Get storage configuration from environment variables.

    Returns
    -------
    dict
        Dictionary with configuration:
        - mode: "local" or "cloud"
        - bucket: GCS bucket name (cloud mode only)
        - exp_id: Experiment ID
        - run_id: Run ID
        - dir_prefix: Directory prefix (e.g., "pipeline/flu/")

    Raises
    ------
    ValueError
        If EXP_ID is not set in environment
    """
    exp_id = os.getenv("EXP_ID")
    if not exp_id:
        raise ValueError(
            "EXP_ID environment variable is required but not set. "
            "Set it before running: export EXP_ID=your-experiment-id"
        )

    # Get RUN_ID - if not set or empty, use "unknown"
    run_id = os.getenv("RUN_ID") or "unknown"

    return {
        "mode": _get_execution_mode(),
        "bucket": os.getenv("GCS_BUCKET", ""),
        "exp_id": exp_id,
        "run_id": run_id,
        "dir_prefix": os.getenv("DIR_PREFIX", "pipeline/flu/").rstrip("/"),
    }


def get_path(*parts: str) -> str:
    """Construct a storage path from components.

    Uses DIR_PREFIX from environment (e.g., "pipeline/flu/") plus EXP_ID and RUN_ID.

    In local mode: Returns path like "bucket/{dir_prefix}/{exp_id}/{run_id}/{parts}"
    In cloud mode: Returns path like "{dir_prefix}/{exp_id}/{run_id}/{parts}"

    Parameters
    ----------
    *parts : str
        Path components to join (e.g., "builder-artifacts", "input_0000.pkl")

    Returns
    -------
    str
        Full storage path string

    Examples
    --------
    With DIR_PREFIX=pipeline/flu/, EXP_ID=test-sim, RUN_ID=run-20241015
    >>> get_path("builder-artifacts", "input_0000.pkl")
    # Local: "bucket/pipeline/flu/test-sim/run-20241015/builder-artifacts/input_0000.pkl"
    # Cloud: "pipeline/flu/test-sim/run-20241015/builder-artifacts/input_0000.pkl"
    """
    config = get_config()
    mode = config["mode"]

    # Build the base path structure using DIR_PREFIX
    base_parts = [config["dir_prefix"], config["exp_id"], config["run_id"]]
    full_parts = base_parts + list(parts)

    if mode == "local":
        # Prefix with "bucket/" for local mode
        return "bucket/" + "/".join(full_parts)
    else:
        # No bucket prefix for cloud mode
        return "/".join(full_parts)


def _resolve_storage_location(path: str) -> tuple[str | None, str]:
    """Resolve the storage location from a path.

    In local mode:
        - Returns (None, path) - path is used as filesystem path

    In cloud mode:
        - Gets bucket from GCS_BUCKET env var
        - Strips "bucket/" prefix if present
        - Returns (bucket_name, clean_path)

    Parameters
    ----------
    path : str
        Storage path (may have "bucket/" prefix from local mode)

    Returns
    -------
    tuple[Optional[str], str]
        Tuple of (bucket_name, final_path)
    """
    config = get_config()
    mode = config["mode"]

    if mode == "local":
        # Local mode: use path as-is
        return None, path
    else:
        # Cloud mode: get bucket from env and clean path
        bucket = config["bucket"]
        if not bucket:
            raise ValueError("Cloud mode requires GCS_BUCKET environment variable to be set")

        # Strip "bucket/" prefix if present (for paths generated in local mode)
        clean_path = path
        if path.startswith("bucket/"):
            clean_path = "/".join(path.split("/")[1:])

        return bucket, clean_path


def load_bytes(path: str) -> bytes:
    """Load bytes from storage.

    In cloud mode: Downloads from GCS bucket (using GCS_BUCKET env var)
    In local mode: Reads from local filesystem at /data/{path}

    Parameters
    ----------
    path : str
        Storage path (generated by get_path() or custom)

    Returns
    -------
    bytes
        File contents as bytes

    Raises
    ------
    FileNotFoundError
        If file doesn't exist
    ValueError
        In cloud mode if GCS_BUCKET not set
    Exception
        For GCS errors in cloud mode
    """
    mode = _get_execution_mode()
    bucket_name, final_path = _resolve_storage_location(path)

    if mode == "local":
        # Local filesystem mode
        base_path = _get_local_base_path()
        file_path = base_path / final_path

        if not file_path.exists():
            raise FileNotFoundError(f"Local file not found: {file_path}")

        data = file_path.read_bytes()
        _storage_logger.log_read(str(file_path), len(data))
        return data

    else:
        # Cloud mode - use GCS
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(final_path)

        data = blob.download_as_bytes()
        _storage_logger.log_read(f"gs://{bucket_name}/{final_path}", len(data))
        return data


def save_bytes(path: str, data: bytes) -> None:
    """Save bytes to storage.

    In cloud mode: Uploads to GCS bucket (using GCS_BUCKET env var)
    In local mode: Writes to local filesystem at /data/{path}

    Parameters
    ----------
    path : str
        Storage path (generated by get_path() or custom)
    data : bytes
        File contents as bytes

    Raises
    ------
    ValueError
        In cloud mode if GCS_BUCKET not set
    Exception
        For I/O or GCS errors
    """
    mode = _get_execution_mode()
    bucket_name, final_path = _resolve_storage_location(path)

    if mode == "local":
        # Local filesystem mode
        base_path = _get_local_base_path()
        file_path = base_path / final_path

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle both bytes and str (in case to_csv returns str instead of bytes)
        if isinstance(data, str):
            data = data.encode("utf-8")

        file_path.write_bytes(data)
        _storage_logger.log_write(str(file_path), len(data))

    else:
        # Cloud mode - use GCS
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(final_path)

        # Handle both bytes and str (in case to_csv returns str instead of bytes)
        if isinstance(data, str):
            data = data.encode("utf-8")

        blob.upload_from_string(data)
        _storage_logger.log_write(f"gs://{bucket_name}/{final_path}", len(data))


def save_json(path: str, data: dict) -> None:
    """Save dictionary as JSON file to storage.

    Parameters
    ----------
    path : str
        Storage path (generated by get_path() or custom)
    data : dict
        Dictionary to save as JSON

    Raises
    ------
    ValueError
        In cloud mode if GCS_BUCKET not set
    Exception
        For I/O or GCS errors
    """
    import json

    json_bytes = json.dumps(data, indent=2).encode("utf-8")
    save_bytes(path, json_bytes)


def load_json(path: str) -> dict:
    """Load JSON file from storage as dictionary.

    Parameters
    ----------
    path : str
        Storage path (generated by get_path() or custom)

    Returns
    -------
    dict
        Parsed JSON data

    Raises
    ------
    FileNotFoundError
        If file doesn't exist
    ValueError
        In cloud mode if GCS_BUCKET not set
    Exception
        For GCS errors or JSON parsing errors
    """
    import json

    json_bytes = load_bytes(path)
    return json.loads(json_bytes.decode("utf-8"))


def save_telemetry_summary(
    telemetry: "ExecutionTelemetry",
    summary_name: str,
    verbose: bool = True,
) -> tuple[str, str]:
    """Save telemetry summary in both JSON and TXT formats.

    Saves telemetry to both:
    - summaries/json/{summary_name}.json
    - summaries/txt/{summary_name}.txt

    Parameters
    ----------
    telemetry : ExecutionTelemetry
        Telemetry object to save
    summary_name : str
        Base name for summary files (without extension).
        Must not contain path separators.
        Examples: "builder_summary", "runner_0042_summary", "workflow_summary"
    verbose : bool, optional
        Whether to print save confirmations (default: True)

    Returns
    -------
    tuple[str, str]
        Tuple of (json_path, txt_path) for saved files

    Raises
    ------
    ValueError
        If summary_name contains path separators

    Examples
    --------
    >>> save_telemetry_summary(builder_telemetry, "builder_summary")
    ('summaries/json/builder_summary.json', 'summaries/txt/builder_summary.txt')

    >>> save_telemetry_summary(runner_telemetry, f"runner_{idx:04d}_summary")
    ('summaries/json/runner_0000_summary.json', 'summaries/txt/runner_0000_summary.txt')
    """
    # Validate summary_name doesn't contain path traversal
    if "/" in summary_name or "\\" in summary_name:
        raise ValueError(f"Invalid summary_name: must not contain path separators: {summary_name}")

    # Save as JSON
    json_path = get_path("summaries", "json", f"{summary_name}.json")
    save_json(json_path, telemetry.to_dict())
    if verbose:
        _logger.debug(f"Saved JSON summary: {json_path}")

    # Save as TXT
    txt_path = get_path("summaries", "txt", f"{summary_name}.txt")
    txt_content = telemetry.to_text()
    save_bytes(txt_path, txt_content.encode("utf-8"))
    if verbose:
        _logger.debug(f"Saved TXT summary: {txt_path}")

    return json_path, txt_path


def list_blobs(bucket_name: str | None, prefix: str = "") -> list[str]:
    """
    List all blob paths in storage with given prefix.

    In cloud mode: Lists blobs in GCS bucket
    In local mode: Lists files in local filesystem

    Args:
        bucket_name: GCS bucket name (required in cloud mode, can be None in local mode)
        prefix: Path prefix to filter results

    Returns:
        List of blob/file paths
    """
    mode = _get_execution_mode()

    if mode == "local":
        # Local filesystem mode
        base_path = _get_local_base_path()
        search_path = base_path / prefix if prefix else base_path

        if not search_path.exists():
            return []

        # Find all files recursively under the prefix path
        files = []
        if search_path.is_file():
            files = [str(search_path.relative_to(base_path))]
        else:
            for file_path in search_path.rglob("*"):
                if file_path.is_file():
                    files.append(str(file_path.relative_to(base_path)))

        return sorted(files)

    else:
        # Cloud mode - use GCS
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)

        return sorted([blob.name for blob in blobs])


def get_mode_info() -> dict[str, str]:
    """
    Get information about the current storage mode.

    Returns:
        Dictionary with mode information
    """
    mode = _get_execution_mode()
    info = {"mode": mode}

    if mode == "local":
        info["base_path"] = str(_get_local_base_path())

    return info
