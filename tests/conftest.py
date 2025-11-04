"""Pytest configuration and shared fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Add scripts directory to path for imports
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def temp_local_path(tmp_path):
    """Provide a temporary local data path for testing.

    Returns
    -------
    Path
        Temporary directory path that can be used as LOCAL_DATA_PATH
    """
    return tmp_path


@pytest.fixture
def mock_env_local(monkeypatch, temp_local_path):
    """Set up environment variables for local mode testing.

    Sets up minimal environment for local filesystem operations.
    """
    monkeypatch.setenv("EXECUTION_MODE", "local")
    monkeypatch.setenv("EXP_ID", "test-exp")
    monkeypatch.setenv("RUN_ID", "test-run")
    monkeypatch.setenv("DIR_PREFIX", "pipeline/test/")
    monkeypatch.setenv("LOCAL_DATA_PATH", str(temp_local_path))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("STORAGE_VERBOSE", "false")
    return {
        "exp_id": "test-exp",
        "run_id": "test-run",
        "dir_prefix": "pipeline/test/",
        "local_path": temp_local_path,
    }


@pytest.fixture
def mock_env_cloud(monkeypatch):
    """Set up environment variables for cloud mode testing.

    Sets up minimal environment for GCS operations (no actual credentials).
    """
    monkeypatch.setenv("EXECUTION_MODE", "cloud")
    monkeypatch.setenv("EXP_ID", "test-exp")
    monkeypatch.setenv("RUN_ID", "test-run")
    monkeypatch.setenv("DIR_PREFIX", "pipeline/test/")
    monkeypatch.setenv("GCS_BUCKET", "test-bucket")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("STORAGE_VERBOSE", "false")
    return {
        "exp_id": "test-exp",
        "run_id": "test-run",
        "dir_prefix": "pipeline/test/",
        "bucket": "test-bucket",
    }
