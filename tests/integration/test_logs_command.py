"""Integration tests for logs command."""

import json
from subprocess import CalledProcessError
from unittest.mock import Mock, patch

import pytest

from epycloud.commands import logs


class TestLogsCommand:
    """Test logs command main handler."""

    @patch("epycloud.commands.logs.subprocess.run")
    def test_logs_fetch_by_exp_id(self, mock_subprocess, mock_config):
        """Test fetching logs by experiment ID."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "timestamp": "2025-11-16T10:00:00Z",
                        "severity": "INFO",
                        "textPayload": "Starting pipeline",
                        "labels": {"exp_id": "test-exp", "stage": "A"},
                    }
                ]
            ),
            stderr="",
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id=None,
                stage=None,
                task_index=None,
                follow=False,
                tail=100,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called
        # Verify filter includes exp_id
        cmd = mock_subprocess.call_args[0][0]
        filter_arg = cmd[3]
        assert 'labels.exp_id="test-exp"' in filter_arg

    @patch("epycloud.commands.logs.subprocess.run")
    def test_logs_fetch_by_stage(self, mock_subprocess, mock_config):
        """Test filtering logs by stage."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps([]),
            stderr="",
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id=None,
                stage="runner",
                task_index=None,
                follow=False,
                tail=100,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 0
        cmd = mock_subprocess.call_args[0][0]
        filter_arg = cmd[3]
        assert 'labels.stage="B"' in filter_arg

    @patch("epycloud.commands.logs.subprocess.run")
    def test_logs_fetch_by_run_id(self, mock_subprocess, mock_config):
        """Test filtering logs by run_id."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps([]),
            stderr="",
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id="20251116-100000-abc123",
                stage=None,
                task_index=None,
                follow=False,
                tail=100,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 0
        cmd = mock_subprocess.call_args[0][0]
        filter_arg = cmd[3]
        assert 'labels.run_id="20251116-100000-abc123"' in filter_arg

    @patch("epycloud.commands.logs.subprocess.run")
    def test_logs_fetch_with_task_index(self, mock_subprocess, mock_config):
        """Test filtering logs by task index."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps([]),
            stderr="",
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id=None,
                stage="runner",
                task_index=5,
                follow=False,
                tail=100,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 0
        cmd = mock_subprocess.call_args[0][0]
        filter_arg = cmd[3]
        assert 'labels.batch.task_index="5"' in filter_arg

    @patch("epycloud.commands.logs.subprocess.run")
    def test_logs_tail_limit(self, mock_subprocess, mock_config):
        """Test limiting log entries with tail parameter."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps([]),
            stderr="",
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id=None,
                stage=None,
                task_index=None,
                follow=False,
                tail=500,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 0
        cmd = mock_subprocess.call_args[0][0]
        assert "--limit=500" in cmd

    @patch("epycloud.commands.logs.subprocess.run")
    def test_logs_tail_unlimited(self, mock_subprocess, mock_config):
        """Test tail=0 for unlimited logs."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps([]),
            stderr="",
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id=None,
                stage=None,
                task_index=None,
                follow=False,
                tail=0,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 0
        cmd = mock_subprocess.call_args[0][0]
        # Should not have --limit flag
        assert not any("--limit" in str(arg) for arg in cmd)

    @patch("epycloud.commands.logs.subprocess.run")
    def test_logs_empty_result(self, mock_subprocess, mock_config):
        """Test handling when no logs found."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="",
            stderr="",
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id=None,
                stage=None,
                task_index=None,
                follow=False,
                tail=100,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.logs.subprocess.run")
    def test_logs_gcloud_error(self, mock_subprocess, mock_config):
        """Test handling gcloud command failure."""
        mock_subprocess.side_effect = CalledProcessError(
            returncode=1,
            cmd=["gcloud", "logging", "read"],
            stderr="Permission denied",
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id=None,
                stage=None,
                task_index=None,
                follow=False,
                tail=100,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.logs.subprocess.run")
    def test_logs_with_severity_filter(self, mock_subprocess, mock_config):
        """Test filtering logs by severity level."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps([]),
            stderr="",
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id=None,
                stage=None,
                task_index=None,
                follow=False,
                tail=100,
                since=None,
                level="ERROR",
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 0
        cmd = mock_subprocess.call_args[0][0]
        filter_arg = cmd[3]
        assert 'severity="ERROR"' in filter_arg

    def test_logs_invalid_exp_id(self, mock_config):
        """Test validation error for invalid exp_id."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="../invalid",
                run_id=None,
                stage=None,
                task_index=None,
                follow=False,
                tail=100,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 1

    def test_logs_invalid_run_id(self, mock_config):
        """Test validation error for invalid run_id."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id="invalid-format",
                stage=None,
                task_index=None,
                follow=False,
                tail=100,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 1

    def test_logs_missing_config(self):
        """Test error when config is missing."""
        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "dry_run": False,
            "args": Mock(exp_id="test-exp"),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 2

    def test_logs_missing_project_id(self):
        """Test error when project_id not configured."""
        config = {
            "google_cloud": {
                "region": "us-central1",
                # Missing project_id
            }
        }

        ctx = {
            "config": config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id=None,
                stage=None,
                task_index=None,
                follow=False,
                tail=100,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 2


class TestLogsNormalizeStage:
    """Test stage name normalization."""

    def test_normalize_stage_builder_to_a(self):
        """Test builder -> A conversion."""
        result = logs._normalize_stage_name("builder")
        assert result == "A"

    def test_normalize_stage_runner_to_b(self):
        """Test runner -> B conversion."""
        result = logs._normalize_stage_name("runner")
        assert result == "B"

    def test_normalize_stage_output_to_c(self):
        """Test output -> C conversion."""
        result = logs._normalize_stage_name("output")
        assert result == "C"

    def test_normalize_stage_a_unchanged(self):
        """Test A stays as A."""
        result = logs._normalize_stage_name("A")
        assert result == "A"

    def test_normalize_stage_b_unchanged(self):
        """Test B stays as B."""
        result = logs._normalize_stage_name("B")
        assert result == "B"

    def test_normalize_stage_c_unchanged(self):
        """Test C stays as C."""
        result = logs._normalize_stage_name("C")
        assert result == "C"

    def test_normalize_stage_lowercase(self):
        """Test lowercase a -> A."""
        result = logs._normalize_stage_name("a")
        assert result == "A"


class TestLogsParseSinceTime:
    """Test since time parsing."""

    def test_parse_since_time_hours(self):
        """Test parsing hours."""
        result = logs._parse_since_time("1h")
        assert result is not None
        # Result is a datetime object
        from datetime import datetime

        assert isinstance(result, datetime)

    def test_parse_since_time_minutes(self):
        """Test parsing minutes."""
        result = logs._parse_since_time("30m")
        assert result is not None

    def test_parse_since_time_days(self):
        """Test parsing days."""
        result = logs._parse_since_time("7d")
        assert result is not None

    def test_parse_since_time_invalid(self):
        """Test invalid since time."""
        result = logs._parse_since_time("invalid")
        # Should return None for invalid format
        assert result is None


class TestLogsFollowMode:
    """Test logs follow mode."""

    @patch("epycloud.commands.logs.time.sleep")
    @patch("epycloud.commands.logs.subprocess.run")
    def test_logs_follow_mode_stops_on_keyboard_interrupt(
        self, mock_subprocess, mock_sleep, mock_config
    ):
        """Test follow mode stops on Ctrl+C."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps([]),
            stderr="",
        )
        # Simulate Ctrl+C after first poll
        mock_sleep.side_effect = KeyboardInterrupt()

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id=None,
                stage=None,
                task_index=None,
                follow=True,
                tail=100,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.logs.time.sleep")
    @patch("epycloud.commands.logs.subprocess.run")
    def test_logs_follow_mode_streams_new_logs(
        self, mock_subprocess, mock_sleep, mock_config
    ):
        """Test follow mode fetches and displays logs."""
        # First call returns logs
        first_response = Mock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "timestamp": "2025-11-16T10:00:00Z",
                        "severity": "INFO",
                        "textPayload": "Log entry 1",
                    }
                ]
            ),
            stderr="",
        )

        # Second call raises KeyboardInterrupt
        call_count = [0]

        def subprocess_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 1:
                return first_response
            raise CalledProcessError(1, "gcloud")

        mock_subprocess.side_effect = subprocess_side_effect
        mock_sleep.side_effect = KeyboardInterrupt()

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                exp_id="test-exp",
                run_id=None,
                stage=None,
                task_index=None,
                follow=True,
                tail=100,
                since=None,
                level=None,
            ),
        }

        exit_code = logs.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called


class TestLogsDisplayFormat:
    """Test log display formatting."""

    def test_display_logs_with_text_payload(self):
        """Test displaying logs with text payload."""
        test_logs = [
            {
                "timestamp": "2025-11-16T10:00:00Z",
                "severity": "INFO",
                "textPayload": "Test message",
                "labels": {"stage": "A"},
            }
        ]
        # Should not raise an error
        logs._display_logs(test_logs)

    def test_display_logs_with_json_payload(self):
        """Test displaying logs with JSON payload."""
        test_logs = [
            {
                "timestamp": "2025-11-16T10:00:00Z",
                "severity": "WARNING",
                "jsonPayload": {"message": "JSON message", "data": "value"},
                "labels": {"stage": "B", "batch.task_index": "5"},
            }
        ]
        # Should not raise an error
        logs._display_logs(test_logs)

    def test_display_logs_empty_list(self):
        """Test displaying empty log list."""
        logs._display_logs([])

    def test_display_logs_missing_fields(self):
        """Test displaying logs with missing fields."""
        test_logs = [
            {
                "severity": "ERROR",
                # Missing timestamp and payload
            }
        ]
        # Should handle gracefully
        logs._display_logs(test_logs)
