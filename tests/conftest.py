"""Pytest configuration and shared fixtures."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock

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


# ========== Integration Test Fixtures ==========


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory.

    Parameters
    ----------
    tmp_path : Path
        Pytest temporary directory fixture.

    Returns
    -------
    Path
        Path to temporary config directory.
    """
    config_dir = tmp_path / ".config" / "epymodelingsuite-cloud"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def mock_config():
    """Standard test configuration.

    Returns
    -------
    dict
        Test configuration dictionary.
    """
    return {
        "google_cloud": {
            "project_id": "test-project",
            "region": "us-central1",
            "bucket_name": "test-bucket",
        },
        "docker": {
            "registry": "us-central1-docker.pkg.dev",
            "repo_name": "epymodelingsuite-repo",
            "image_name": "epymodelingsuite",
            "image_tag": "latest",
        },
        "github": {
            "forecast_repo": "test-org/test-repo",
        },
        "pipeline": {
            "dir_prefix": "pipeline/test/",
            "max_parallelism": 100,
        },
        "resources": {
            "stage_a": {
                "cpu_milli": 2000,
                "memory_mib": 8192,
                "max_run_duration": 3600,
            },
            "stage_b": {
                "cpu_milli": 4000,
                "memory_mib": 16384,
                "max_run_duration": 7200,
            },
            "stage_c": {
                "cpu_milli": 2000,
                "memory_mib": 8192,
                "max_run_duration": 1800,
            },
        },
    }


@pytest.fixture
def mock_gcloud_subprocess(monkeypatch):
    """Mock gcloud subprocess calls.

    Parameters
    ----------
    monkeypatch : MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    Mock
        Mock subprocess.run function.
    """
    mock_run = Mock()
    mock_run.return_value = Mock(returncode=0, stdout="mock-access-token\n", stderr="")
    monkeypatch.setattr("subprocess.run", mock_run)
    return mock_run
