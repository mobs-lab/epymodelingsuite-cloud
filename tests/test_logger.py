"""Tests for scripts/util/logger.py module."""

import json

import pytest
from util import logger


@pytest.mark.unit
class TestSetupLogger:
    """Tests for setup_logger() function."""

    def test_setup_logger_local_mode(self, monkeypatch, capfd):
        """Test setup_logger creates console logger in local mode."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        test_logger = logger.setup_logger("test-stage")
        test_logger.info("Test message")

        captured = capfd.readouterr()
        assert "test-stage" in captured.out
        assert "INFO" in captured.out
        assert "Test message" in captured.out

    def test_setup_logger_cloud_mode(self, monkeypatch, capfd):
        """Test setup_logger creates JSON logger in cloud mode."""
        monkeypatch.setenv("EXECUTION_MODE", "cloud")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        test_logger = logger.setup_logger("test-stage", exp_id="test-exp")
        test_logger.info("Test message")

        captured = capfd.readouterr()
        # Should be valid JSON
        log_line = captured.out.strip()
        log_data = json.loads(log_line)

        assert log_data["stage"] == "test-stage"
        assert log_data["severity"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["exp_id"] == "test-exp"

    def test_setup_logger_respects_log_level(self, monkeypatch, capfd):
        """Test setup_logger respects LOG_LEVEL environment variable."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")

        test_logger = logger.setup_logger("test-stage")

        # INFO should not be logged
        test_logger.info("Info message")
        captured_info = capfd.readouterr()
        assert "Info message" not in captured_info.out

        # WARNING should be logged
        test_logger.warning("Warning message")
        captured_warning = capfd.readouterr()
        assert "Warning message" in captured_warning.out

    def test_setup_logger_default_log_level(self, monkeypatch, capfd):
        """Test setup_logger defaults to INFO level."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.delenv("LOG_LEVEL", raising=False)

        test_logger = logger.setup_logger("test-stage")

        # DEBUG should not be logged
        test_logger.debug("Debug message")
        captured_debug = capfd.readouterr()
        assert "Debug message" not in captured_debug.out

        # INFO should be logged
        test_logger.info("Info message")
        captured_info = capfd.readouterr()
        assert "Info message" in captured_info.out

    def test_setup_logger_adds_task_index(self, monkeypatch, capfd):
        """Test setup_logger includes task index in logs."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        test_logger = logger.setup_logger("runner", task_index=42)
        test_logger.info("Task message")

        captured = capfd.readouterr()
        assert "[Task 42]" in captured.out

    def test_setup_logger_cloud_adds_context_fields(self, monkeypatch, capfd):
        """Test setup_logger adds exp_id, run_id, task_index to JSON logs."""
        monkeypatch.setenv("EXECUTION_MODE", "cloud")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        test_logger = logger.setup_logger(
            "runner", task_index=42, exp_id="test-exp", run_id="test-run"
        )
        test_logger.info("Test message")

        captured = capfd.readouterr()
        log_data = json.loads(captured.out.strip())

        assert log_data["stage"] == "runner"
        assert log_data["task_index"] == 42
        assert log_data["exp_id"] == "test-exp"
        assert log_data["run_id"] == "test-run"

    def test_setup_logger_cloud_extra_fields(self, monkeypatch, capfd):
        """Test setup_logger includes extra fields in JSON logs."""
        monkeypatch.setenv("EXECUTION_MODE", "cloud")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        test_logger = logger.setup_logger("test-stage")
        test_logger.info("Test message", extra={"custom_field": "custom_value"})

        captured = capfd.readouterr()
        log_data = json.loads(captured.out.strip())

        assert log_data["custom_field"] == "custom_value"

    def test_setup_logger_no_propagation(self, monkeypatch):
        """Test setup_logger disables propagation to prevent duplicate logs."""
        monkeypatch.setenv("EXECUTION_MODE", "local")

        test_logger = logger.setup_logger("test-stage")

        assert test_logger.propagate is False

    def test_setup_logger_clears_handlers(self, monkeypatch):
        """Test setup_logger clears existing handlers to avoid duplicates."""
        monkeypatch.setenv("EXECUTION_MODE", "local")

        # Call twice with same name
        test_logger1 = logger.setup_logger("test-stage")
        handler_count1 = len(test_logger1.handlers)

        test_logger2 = logger.setup_logger("test-stage")
        handler_count2 = len(test_logger2.handlers)

        # Should have same number of handlers (not accumulate)
        assert handler_count1 == handler_count2
        assert handler_count2 == 1


@pytest.mark.unit
class TestStorageLogger:
    """Tests for StorageLogger class."""

    def test_storage_logger_verbose_true(self, monkeypatch, capfd):
        """Test StorageLogger logs when STORAGE_VERBOSE=true."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("STORAGE_VERBOSE", "true")

        test_logger = logger.setup_logger("storage")
        storage_logger = logger.StorageLogger(test_logger)

        storage_logger.log_read("/path/to/file.txt", 1024)
        captured = capfd.readouterr()

        assert "Read 1,024 bytes from /path/to/file.txt" in captured.out

    def test_storage_logger_verbose_false(self, monkeypatch, capfd):
        """Test StorageLogger doesn't log when STORAGE_VERBOSE=false."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("STORAGE_VERBOSE", "false")

        test_logger = logger.setup_logger("storage")
        storage_logger = logger.StorageLogger(test_logger)

        storage_logger.log_read("/path/to/file.txt", 1024)
        captured = capfd.readouterr()

        assert "Read" not in captured.out

    def test_storage_logger_default_verbose_false(self, monkeypatch, capfd):
        """Test StorageLogger defaults to verbose=false."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.delenv("STORAGE_VERBOSE", raising=False)

        test_logger = logger.setup_logger("storage")
        storage_logger = logger.StorageLogger(test_logger)

        storage_logger.log_read("/path/to/file.txt", 1024)
        captured = capfd.readouterr()

        assert "Read" not in captured.out

    def test_storage_logger_log_write(self, monkeypatch, capfd):
        """Test StorageLogger.log_write() with verbose mode."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("STORAGE_VERBOSE", "true")

        test_logger = logger.setup_logger("storage")
        storage_logger = logger.StorageLogger(test_logger)

        storage_logger.log_write("/path/to/output.txt", 2048)
        captured = capfd.readouterr()

        assert "Wrote 2,048 bytes to /path/to/output.txt" in captured.out

    def test_storage_logger_log_operation_always_logged(self, monkeypatch, capfd):
        """Test StorageLogger.log_operation() always logs regardless of verbose."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "INFO")
        monkeypatch.setenv("STORAGE_VERBOSE", "false")

        test_logger = logger.setup_logger("storage")
        storage_logger = logger.StorageLogger(test_logger)

        storage_logger.log_operation("Upload", "gs://bucket/file.pkl")
        captured = capfd.readouterr()

        # Should be logged even with verbose=false
        assert "Upload: gs://bucket/file.pkl" in captured.out

    def test_storage_logger_number_formatting(self, monkeypatch, capfd):
        """Test StorageLogger formats large numbers with commas."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("STORAGE_VERBOSE", "true")

        test_logger = logger.setup_logger("storage")
        storage_logger = logger.StorageLogger(test_logger)

        storage_logger.log_read("/path/to/file.txt", 1234567)
        captured = capfd.readouterr()

        assert "1,234,567" in captured.out


@pytest.mark.unit
class TestCloudFormatter:
    """Tests for cloud JSON formatter."""

    @pytest.mark.skip(reason="pythonjsonlogger is installed, cannot test ImportError")
    def test_cloud_formatter_requires_pythonjsonlogger(self, monkeypatch):
        """Test cloud formatter raises error if python-json-logger not installed.

        Note: This test is skipped when pythonjsonlogger is already installed.
        The error handling is verified manually during package installation.
        """
        monkeypatch.setenv("EXECUTION_MODE", "cloud")

        # Mock ImportError when importing pythonjsonlogger
        from unittest.mock import MagicMock

        mock_module = MagicMock()
        mock_module.jsonlogger.side_effect = ImportError()

        with pytest.raises(ImportError, match="python-json-logger is required"):
            # This will trigger the import in _create_cloud_formatter
            logger.setup_logger("test-stage")

    def test_cloud_formatter_severity_mapping(self, monkeypatch, capfd):
        """Test cloud formatter renames levelname to severity."""
        monkeypatch.setenv("EXECUTION_MODE", "cloud")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")

        test_logger = logger.setup_logger("test-stage")
        test_logger.warning("Warning message")

        captured = capfd.readouterr()
        log_data = json.loads(captured.out.strip())

        # Should have 'severity' not 'levelname'
        assert "severity" in log_data
        assert "levelname" not in log_data
        assert log_data["severity"] == "WARNING"


@pytest.mark.unit
class TestLocalFormatter:
    """Tests for local console formatter."""

    def test_local_formatter_without_task_index(self, monkeypatch, capfd):
        """Test local formatter output without task index."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        test_logger = logger.setup_logger("builder")
        test_logger.info("Test message")

        captured = capfd.readouterr()
        assert "builder" in captured.out
        assert "INFO" in captured.out
        assert "Test message" in captured.out
        assert "[Task" not in captured.out

    def test_local_formatter_with_task_index(self, monkeypatch, capfd):
        """Test local formatter output with task index."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        test_logger = logger.setup_logger("runner", task_index=7)
        test_logger.info("Test message")

        captured = capfd.readouterr()
        assert "runner" in captured.out
        assert "[Task 7]" in captured.out
        assert "Test message" in captured.out

    def test_local_formatter_timestamp_format(self, monkeypatch, capfd):
        """Test local formatter includes human-readable timestamp."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        test_logger = logger.setup_logger("test-stage")
        test_logger.info("Test message")

        captured = capfd.readouterr()
        # Should have timestamp in format: YYYY-MM-DD HH:MM:SS
        import re

        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        assert re.search(timestamp_pattern, captured.out)
