"""
Storage abstraction layer for switching between GCS and local filesystem.

Supports two execution modes via EXECUTION_MODE environment variable:
- 'cloud': Uses Google Cloud Storage API
- 'local': Uses filesystem operations at /data mount

Usage:
    from util.storage import load_bytes, save_bytes

    # Works in both local and cloud modes
    data = load_bytes("my-bucket", "path/to/file.pkl")
    save_bytes("my-bucket", "path/to/output.pkl", data)
"""

import os
from pathlib import Path
from typing import Optional


def _get_execution_mode() -> str:
    """Get the execution mode from environment variable."""
    return os.getenv("EXECUTION_MODE", "cloud").lower()


def _get_local_base_path() -> Path:
    """Get the base path for local storage."""
    return Path(os.getenv("LOCAL_DATA_PATH", "/data"))


def load_bytes(bucket_name: Optional[str], path: str) -> bytes:
    """
    Load bytes from storage.

    In cloud mode: Downloads from GCS bucket
    In local mode: Reads from local filesystem at /data/{path}

    Args:
        bucket_name: GCS bucket name (required in cloud mode, can be None in local mode)
        path: Path to the file relative to bucket root

    Returns:
        File contents as bytes

    Raises:
        FileNotFoundError: If file doesn't exist
        Exception: For GCS errors in cloud mode

    Note:
        In local mode, bucket_name is ignored and can be None.
        The file is read directly from {LOCAL_DATA_PATH}/{path}.
    """
    mode = _get_execution_mode()

    if mode == "local":
        # Local filesystem mode
        base_path = _get_local_base_path()
        file_path = base_path / path

        if not file_path.exists():
            raise FileNotFoundError(f"Local file not found: {file_path}")

        print(f"[Local Storage] Reading: {file_path}")
        return file_path.read_bytes()

    else:
        # Cloud mode - use GCS
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(path)

        print(f"[GCS] Downloading: gs://{bucket_name}/{path}")
        return blob.download_as_bytes()


def save_bytes(bucket_name: Optional[str], path: str, data: bytes) -> None:
    """
    Save bytes to storage.

    In cloud mode: Uploads to GCS bucket
    In local mode: Writes to local filesystem at /data/{path}

    Args:
        bucket_name: GCS bucket name (required in cloud mode, can be None in local mode)
        path: Path to the file relative to bucket root
        data: File contents as bytes

    Raises:
        Exception: For I/O or GCS errors

    Note:
        In local mode, bucket_name is ignored and can be None.
        The file is written directly to {LOCAL_DATA_PATH}/{path}.
        Parent directories are created automatically if they don't exist.
    """
    mode = _get_execution_mode()

    if mode == "local":
        # Local filesystem mode
        base_path = _get_local_base_path()
        file_path = base_path / path

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[Local Storage] Writing: {file_path} ({len(data)} bytes)")
        file_path.write_bytes(data)

    else:
        # Cloud mode - use GCS
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(path)

        print(f"[GCS] Uploading: gs://{bucket_name}/{path} ({len(data)} bytes)")
        blob.upload_from_string(data)


def list_blobs(bucket_name: Optional[str], prefix: str = "") -> list[str]:
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
        from google.cloud import storage

        client = storage.Client()
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
