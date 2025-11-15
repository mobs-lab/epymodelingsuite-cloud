"""Tests for scripts/util/storage.py module."""

import json
from unittest.mock import MagicMock, patch

import pytest
from util import storage


@pytest.mark.unit
class TestGetConfig:
    """Tests for get_config() function."""

    def test_get_config_local_mode(self, mock_env_local):
        """Test get_config returns correct configuration in local mode."""
        config = storage.get_config()

        assert config["mode"] == "local"
        assert config["exp_id"] == "test-exp"
        assert config["run_id"] == "test-run"
        assert config["dir_prefix"] == "pipeline/test"
        assert config["bucket"] == ""

    def test_get_config_cloud_mode(self, mock_env_cloud):
        """Test get_config returns correct configuration in cloud mode."""
        config = storage.get_config()

        assert config["mode"] == "cloud"
        assert config["exp_id"] == "test-exp"
        assert config["run_id"] == "test-run"
        assert config["dir_prefix"] == "pipeline/test"
        assert config["bucket"] == "test-bucket"

    def test_get_config_missing_exp_id(self, monkeypatch):
        """Test get_config raises ValueError when EXP_ID is not set."""
        monkeypatch.delenv("EXP_ID", raising=False)

        with pytest.raises(ValueError, match="EXP_ID environment variable is required"):
            storage.get_config()

    def test_get_config_default_run_id(self, monkeypatch):
        """Test get_config uses 'unknown' when RUN_ID is not set."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("EXP_ID", "test-exp")
        monkeypatch.delenv("RUN_ID", raising=False)

        config = storage.get_config()
        assert config["run_id"] == "unknown"

    def test_get_config_strips_trailing_slash(self, monkeypatch):
        """Test get_config strips trailing slashes from DIR_PREFIX."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("EXP_ID", "test-exp")
        monkeypatch.setenv("RUN_ID", "test-run")
        monkeypatch.setenv("DIR_PREFIX", "pipeline/test///")

        config = storage.get_config()
        assert config["dir_prefix"] == "pipeline/test"


@pytest.mark.unit
class TestGetPath:
    """Tests for get_path() function."""

    def test_get_path_local_mode(self, mock_env_local):
        """Test get_path constructs correct path in local mode."""
        path = storage.get_path("builder-artifacts", "input_00000.pkl")

        assert path == "bucket/pipeline/test/test-exp/test-run/builder-artifacts/input_00000.pkl"

    def test_get_path_cloud_mode(self, mock_env_cloud):
        """Test get_path constructs correct path in cloud mode."""
        path = storage.get_path("builder-artifacts", "input_00000.pkl")

        assert path == "pipeline/test/test-exp/test-run/builder-artifacts/input_00000.pkl"

    def test_get_path_single_component(self, mock_env_local):
        """Test get_path with single path component."""
        path = storage.get_path("summaries")

        assert path == "bucket/pipeline/test/test-exp/test-run/summaries"

    def test_get_path_multiple_components(self, mock_env_local):
        """Test get_path with multiple path components."""
        path = storage.get_path("summaries", "json", "builder_summary.json")

        assert path == "bucket/pipeline/test/test-exp/test-run/summaries/json/builder_summary.json"


@pytest.mark.unit
@pytest.mark.local
class TestLoadSaveBytesLocal:
    """Tests for load_bytes() and save_bytes() in local mode."""

    def test_save_bytes_creates_file(self, mock_env_local, temp_local_path):
        """Test save_bytes creates file in local mode."""
        data = b"test content"
        path = "bucket/test/file.txt"

        storage.save_bytes(path, data)

        file_path = temp_local_path / path
        assert file_path.exists()
        assert file_path.read_bytes() == data

    def test_save_bytes_creates_directories(self, mock_env_local, temp_local_path):
        """Test save_bytes creates parent directories if they don't exist."""
        data = b"test content"
        path = "bucket/deep/nested/path/file.txt"

        storage.save_bytes(path, data)

        file_path = temp_local_path / path
        assert file_path.exists()
        assert file_path.read_bytes() == data

    def test_save_bytes_handles_string_data(self, mock_env_local, temp_local_path):
        """Test save_bytes converts string to bytes."""
        data = "test string content"
        path = "bucket/test/file.txt"

        storage.save_bytes(path, data)

        file_path = temp_local_path / path
        assert file_path.read_bytes() == b"test string content"

    def test_load_bytes_reads_file(self, mock_env_local, temp_local_path):
        """Test load_bytes reads file in local mode."""
        data = b"test content"
        path = "bucket/test/file.txt"
        file_path = temp_local_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)

        result = storage.load_bytes(path)

        assert result == data

    def test_load_bytes_file_not_found(self, mock_env_local):
        """Test load_bytes raises FileNotFoundError when file doesn't exist."""
        path = "bucket/nonexistent/file.txt"

        with pytest.raises(FileNotFoundError, match="Local file not found"):
            storage.load_bytes(path)


@pytest.mark.unit
class TestSaveLoadJson:
    """Tests for save_json() and load_json() functions."""

    def test_save_load_json_roundtrip(self, mock_env_local, temp_local_path):
        """Test save_json and load_json roundtrip."""
        test_data = {
            "key1": "value1",
            "key2": 42,
            "nested": {"foo": "bar"},
        }
        path = "bucket/test/data.json"

        storage.save_json(path, test_data)
        loaded_data = storage.load_json(path)

        assert loaded_data == test_data

    def test_save_json_pretty_formatted(self, mock_env_local, temp_local_path):
        """Test save_json uses pretty formatting (indent=2)."""
        test_data = {"key": "value"}
        path = "bucket/test/data.json"

        storage.save_json(path, test_data)

        file_path = temp_local_path / path
        content = file_path.read_text()
        assert content == '{\n  "key": "value"\n}'


@pytest.mark.unit
class TestSaveTelemetrySummary:
    """Tests for save_telemetry_summary() function."""

    def test_save_telemetry_summary_creates_both_files(self, mock_env_local, temp_local_path):
        """Test save_telemetry_summary creates both JSON and TXT files."""
        # Create mock telemetry object
        mock_telemetry = MagicMock()
        mock_telemetry.to_dict.return_value = {"duration": 123.45, "status": "success"}
        mock_telemetry.to_text.return_value = "Duration: 123.45s\nStatus: success"

        json_path, txt_path = storage.save_telemetry_summary(
            mock_telemetry, "builder_summary", verbose=False
        )

        # Check JSON file
        json_file_path = temp_local_path / json_path
        assert json_file_path.exists()
        json_data = json.loads(json_file_path.read_text())
        assert json_data == {"duration": 123.45, "status": "success"}

        # Check TXT file
        txt_file_path = temp_local_path / txt_path
        assert txt_file_path.exists()
        assert txt_file_path.read_text() == "Duration: 123.45s\nStatus: success"

    def test_save_telemetry_summary_returns_paths(self, mock_env_local):
        """Test save_telemetry_summary returns correct paths."""
        mock_telemetry = MagicMock()
        mock_telemetry.to_dict.return_value = {}
        mock_telemetry.to_text.return_value = ""

        json_path, txt_path = storage.save_telemetry_summary(
            mock_telemetry, "test_summary", verbose=False
        )

        assert json_path.endswith("summaries/json/test_summary.json")
        assert txt_path.endswith("summaries/txt/test_summary.txt")

    def test_save_telemetry_summary_rejects_path_separators(self, mock_env_local):
        """Test save_telemetry_summary raises ValueError for paths with separators."""
        mock_telemetry = MagicMock()

        with pytest.raises(ValueError, match="must not contain path separators"):
            storage.save_telemetry_summary(mock_telemetry, "invalid/path", verbose=False)

        with pytest.raises(ValueError, match="must not contain path separators"):
            storage.save_telemetry_summary(mock_telemetry, "invalid\\path", verbose=False)


@pytest.mark.unit
@pytest.mark.local
class TestListBlobs:
    """Tests for list_blobs() function in local mode."""

    def test_list_blobs_local_returns_files(self, mock_env_local, temp_local_path):
        """Test list_blobs returns files in local mode."""
        # Create test files
        test_dir = temp_local_path / "test_prefix"
        test_dir.mkdir(parents=True)
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")
        (test_dir / "subdir").mkdir()
        (test_dir / "subdir" / "file3.txt").write_text("content3")

        files = storage.list_blobs(None, "test_prefix")

        assert len(files) == 3
        assert "test_prefix/file1.txt" in files
        assert "test_prefix/file2.txt" in files
        assert "test_prefix/subdir/file3.txt" in files

    def test_list_blobs_local_empty_prefix(self, mock_env_local, temp_local_path):
        """Test list_blobs with empty prefix returns all files."""
        (temp_local_path / "file.txt").write_text("content")

        files = storage.list_blobs(None, "")

        assert "file.txt" in files

    def test_list_blobs_local_nonexistent_prefix(self, mock_env_local, temp_local_path):
        """Test list_blobs returns empty list for nonexistent prefix."""
        files = storage.list_blobs(None, "nonexistent_prefix")

        assert files == []


@pytest.mark.unit
class TestGetModeInfo:
    """Tests for get_mode_info() function."""

    def test_get_mode_info_local(self, mock_env_local, temp_local_path):
        """Test get_mode_info returns mode and base_path in local mode."""
        info = storage.get_mode_info()

        assert info["mode"] == "local"
        assert info["base_path"] == str(temp_local_path)

    def test_get_mode_info_cloud(self, mock_env_cloud):
        """Test get_mode_info returns only mode in cloud mode."""
        info = storage.get_mode_info()

        assert info["mode"] == "cloud"
        assert "base_path" not in info


@pytest.mark.unit
@pytest.mark.cloud
@pytest.mark.skip(reason="Requires google-cloud-storage package (cloud-only dependency)")
class TestGCSClientCaching:
    """Tests for GCS client caching optimization.

    Note: These tests are skipped in local development as they require
    google-cloud-storage. The caching logic can be tested manually in Docker
    or cloud environment.
    """

    def test_gcs_client_cached(self, mock_env_cloud):
        """Test that GCS client is cached and reused."""
        # Reset the cache
        storage._gcs_client = None

        with patch("google.cloud.storage.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # First call creates client
            client1 = storage._get_gcs_client()
            assert client1 is mock_client
            assert mock_client_class.call_count == 1

            # Second call returns cached client
            client2 = storage._get_gcs_client()
            assert client2 is mock_client
            assert mock_client_class.call_count == 1  # Not called again

            # Reset cache for other tests
            storage._gcs_client = None
