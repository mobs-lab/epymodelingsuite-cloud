"""Integration tests for status command."""

import json
from unittest.mock import Mock, patch, call

import pytest

from epycloud.commands import status
from epycloud.commands.status.operations import (
    fetch_active_workflows,
    fetch_active_batch_jobs,
    display_status,
)


class TestStatusShowCommand:
    """Test status show command (one-time check)."""

    @patch("epycloud.commands.status.handlers.fetch_active_batch_jobs")
    @patch("epycloud.commands.status.handlers.fetch_active_workflows")
    @patch("epycloud.commands.status.handlers.get_google_cloud_config")
    @patch("epycloud.commands.status.handlers.require_config")
    def test_status_show_once(
        self,
        mock_require_config,
        mock_gcloud_config,
        mock_fetch_workflows,
        mock_fetch_jobs,
        mock_config,
    ):
        """Test one-time status display."""
        mock_require_config.return_value = mock_config
        mock_gcloud_config.return_value = {
            "project_id": "test-project",
            "region": "us-central1",
        }
        mock_fetch_workflows.return_value = []
        mock_fetch_jobs.return_value = []

        args = Mock(watch=False, exp_id=None, interval=10)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = status.handle(ctx)

        assert exit_code == 0
        mock_fetch_workflows.assert_called_once()
        mock_fetch_jobs.assert_called_once()

    @patch("epycloud.commands.status.handlers.fetch_active_batch_jobs")
    @patch("epycloud.commands.status.handlers.fetch_active_workflows")
    @patch("epycloud.commands.status.handlers.get_google_cloud_config")
    @patch("epycloud.commands.status.handlers.require_config")
    def test_status_no_active_jobs(
        self,
        mock_require_config,
        mock_gcloud_config,
        mock_fetch_workflows,
        mock_fetch_jobs,
        mock_config,
    ):
        """Test status display when no active jobs."""
        mock_require_config.return_value = mock_config
        mock_gcloud_config.return_value = {
            "project_id": "test-project",
            "region": "us-central1",
        }
        mock_fetch_workflows.return_value = []
        mock_fetch_jobs.return_value = []

        args = Mock(watch=False, exp_id=None, interval=10)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = status.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.status.handlers.fetch_active_batch_jobs")
    @patch("epycloud.commands.status.handlers.fetch_active_workflows")
    @patch("epycloud.commands.status.handlers.get_google_cloud_config")
    @patch("epycloud.commands.status.handlers.require_config")
    def test_status_with_active_workflows(
        self,
        mock_require_config,
        mock_gcloud_config,
        mock_fetch_workflows,
        mock_fetch_jobs,
        mock_config,
    ):
        """Test status display with active workflows."""
        mock_require_config.return_value = mock_config
        mock_gcloud_config.return_value = {
            "project_id": "test-project",
            "region": "us-central1",
        }
        mock_fetch_workflows.return_value = [
            {
                "name": "projects/test-project/locations/us-central1/workflows/epymodelingsuite-pipeline/executions/exec-123",
                "argument": '{"exp_id": "test-flu"}',
                "startTime": "2025-11-16T10:00:00Z",
            }
        ]
        mock_fetch_jobs.return_value = []

        args = Mock(watch=False, exp_id=None, interval=10)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = status.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.status.handlers.fetch_active_batch_jobs")
    @patch("epycloud.commands.status.handlers.fetch_active_workflows")
    @patch("epycloud.commands.status.handlers.get_google_cloud_config")
    @patch("epycloud.commands.status.handlers.require_config")
    def test_status_with_active_batch_jobs(
        self,
        mock_require_config,
        mock_gcloud_config,
        mock_fetch_workflows,
        mock_fetch_jobs,
        mock_config,
    ):
        """Test status display with active batch jobs."""
        mock_require_config.return_value = mock_config
        mock_gcloud_config.return_value = {
            "project_id": "test-project",
            "region": "us-central1",
        }
        mock_fetch_workflows.return_value = []
        mock_fetch_jobs.return_value = [
            {
                "name": "projects/test-project/locations/us-central1/jobs/runner-test-flu-123",
                "status": {
                    "state": "RUNNING",
                    "taskGroups": {
                        "group0": {
                            "counts": {
                                "succeeded": 5,
                                "failed": 0,
                                "running": 3,
                                "pending": 2,
                            }
                        }
                    },
                },
                "labels": {
                    "exp_id": "test-flu",
                    "stage": "runner",
                },
            }
        ]

        args = Mock(watch=False, exp_id=None, interval=10)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = status.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.status.handlers.fetch_active_batch_jobs")
    @patch("epycloud.commands.status.handlers.fetch_active_workflows")
    @patch("epycloud.commands.status.handlers.get_google_cloud_config")
    @patch("epycloud.commands.status.handlers.require_config")
    def test_status_filter_by_exp_id(
        self,
        mock_require_config,
        mock_gcloud_config,
        mock_fetch_workflows,
        mock_fetch_jobs,
        mock_config,
    ):
        """Test status filter by experiment ID."""
        mock_require_config.return_value = mock_config
        mock_gcloud_config.return_value = {
            "project_id": "test-project",
            "region": "us-central1",
        }
        mock_fetch_workflows.return_value = []
        mock_fetch_jobs.return_value = []

        args = Mock(watch=False, exp_id="test-flu", interval=10)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = status.handle(ctx)

        assert exit_code == 0
        # Verify exp_id was passed to fetch functions
        call_args = mock_fetch_workflows.call_args
        assert call_args[1]["exp_id"] == "test-flu"


class TestStatusFetchFunctions:
    """Test status fetch helper functions."""

    @patch("epycloud.lib.command_helpers.get_gcloud_access_token")
    @patch("epycloud.commands.status.operations.requests.get")
    def test_fetch_active_workflows_success(self, mock_get, mock_token):
        """Test fetching active workflows from API."""
        mock_token.return_value = "test-token"
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "executions": [
                    {
                        "name": "projects/test/locations/us-central1/workflows/pipeline/executions/exec-1",
                        "argument": '{"exp_id": "test-flu"}',
                        "startTime": "2025-11-16T10:00:00Z",
                    },
                    {
                        "name": "projects/test/locations/us-central1/workflows/pipeline/executions/exec-2",
                        "argument": '{"exp_id": "test-covid"}',
                        "startTime": "2025-11-16T11:00:00Z",
                    },
                ]
            },
        )
        mock_get.return_value.raise_for_status = Mock()


        workflows = fetch_active_workflows(
            project_id="test-project",
            region="us-central1",
            exp_id=None,
            verbose=False,
        )

        assert len(workflows) == 2
        mock_get.assert_called_once()

    @patch("epycloud.lib.command_helpers.get_gcloud_access_token")
    @patch("epycloud.commands.status.operations.requests.get")
    def test_fetch_active_workflows_filter_by_exp_id(self, mock_get, mock_token):
        """Test filtering workflows by exp_id."""
        mock_token.return_value = "test-token"
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "executions": [
                    {
                        "name": "exec-1",
                        "argument": '{"exp_id": "test-flu"}',
                    },
                    {
                        "name": "exec-2",
                        "argument": '{"exp_id": "test-covid"}',
                    },
                ]
            },
        )
        mock_get.return_value.raise_for_status = Mock()


        workflows = fetch_active_workflows(
            project_id="test-project",
            region="us-central1",
            exp_id="test-flu",
            verbose=False,
        )

        assert len(workflows) == 1
        assert "test-flu" in workflows[0]["argument"]

    @patch("epycloud.lib.command_helpers.get_gcloud_access_token")
    @patch("epycloud.commands.status.operations.requests.get")
    def test_fetch_active_workflows_empty(self, mock_get, mock_token):
        """Test empty workflow list."""
        mock_token.return_value = "test-token"
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {"executions": []},
        )
        mock_get.return_value.raise_for_status = Mock()


        workflows = fetch_active_workflows(
            project_id="test-project",
            region="us-central1",
            exp_id=None,
            verbose=False,
        )

        assert len(workflows) == 0

    @patch("epycloud.lib.command_helpers.get_gcloud_access_token")
    @patch("epycloud.commands.status.operations.requests.get")
    def test_fetch_active_workflows_api_error(self, mock_get, mock_token):
        """Test API error resilience."""
        mock_token.return_value = "test-token"
        mock_get.side_effect = Exception("API error")

        workflows = fetch_active_workflows(
            project_id="test-project",
            region="us-central1",
            exp_id=None,
            verbose=False,
        )

        # Should return empty list on error
        assert workflows == []

    @patch("epycloud.commands.status.operations.subprocess.run")
    def test_fetch_active_batch_jobs_success(self, mock_subprocess):
        """Test fetching active batch jobs."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "name": "projects/test/locations/us-central1/jobs/runner-job",
                        "status": {"state": "RUNNING"},
                        "labels": {"exp_id": "test-flu", "stage": "runner"},
                    }
                ]
            ),
            stderr="",
        )

        jobs = fetch_active_batch_jobs(
            project_id="test-project",
            region="us-central1",
            exp_id=None,
            verbose=False,
        )

        assert len(jobs) == 1
        assert jobs[0]["labels"]["stage"] == "runner"

    @patch("epycloud.commands.status.operations.subprocess.run")
    def test_fetch_active_batch_jobs_empty(self, mock_subprocess):
        """Test empty batch jobs list."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="",
            stderr="",
        )

        jobs = fetch_active_batch_jobs(
            project_id="test-project",
            region="us-central1",
            exp_id=None,
            verbose=False,
        )

        assert len(jobs) == 0

    @patch("epycloud.commands.status.operations.subprocess.run")
    def test_fetch_active_batch_jobs_with_exp_id_filter(self, mock_subprocess):
        """Test batch jobs with exp_id filter."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps([]),
            stderr="",
        )

        jobs = fetch_active_batch_jobs(
            project_id="test-project",
            region="us-central1",
            exp_id="test-flu",
            verbose=False,
        )

        # Verify filter was added to command
        call_args = mock_subprocess.call_args[0][0]
        assert any("labels.exp_id=test-flu" in arg for arg in call_args)

    @patch("epycloud.commands.status.operations.subprocess.run")
    def test_fetch_active_batch_jobs_gcloud_error(self, mock_subprocess):
        """Test gcloud error resilience."""
        mock_subprocess.side_effect = Exception("gcloud error")

        jobs = fetch_active_batch_jobs(
            project_id="test-project",
            region="us-central1",
            exp_id=None,
            verbose=False,
        )

        # Should return empty list on error
        assert jobs == []


class TestStatusDisplayFunction:
    """Test status display formatting."""

    def test_display_status_empty(self):
        """Test displaying empty status."""
        # Should not raise any errors
        display_status([], [], None)

    def test_display_status_with_workflows(self):
        """Test displaying workflows."""
        workflows = [
            {
                "name": "projects/p/locations/l/workflows/w/executions/exec-123",
                "argument": '{"exp_id": "test-flu"}',
                "startTime": "2025-11-16T10:00:00Z",
            }
        ]
        # Should not raise any errors
        display_status(workflows, [], None)

    def test_display_status_with_jobs(self):
        """Test displaying batch jobs."""
        jobs = [
            {
                "name": "projects/p/locations/l/jobs/runner-job",
                "status": {
                    "state": "RUNNING",
                    "taskGroups": {
                        "group0": {
                            "counts": {
                                "succeeded": 5,
                                "failed": 1,
                                "running": 4,
                            }
                        }
                    },
                },
                "labels": {"stage": "runner"},
            }
        ]
        # Should not raise any errors
        display_status([], jobs, None)

    def test_display_status_with_filter(self):
        """Test displaying status with filter."""
        # Should not raise any errors
        display_status([], [], "test-flu")

    def test_display_status_invalid_argument_json(self):
        """Test displaying workflow with invalid argument JSON."""
        workflows = [
            {
                "name": "projects/p/locations/l/workflows/w/executions/exec-123",
                "argument": "invalid-json",
                "startTime": "2025-11-16T10:00:00Z",
            }
        ]
        # Should handle gracefully
        display_status(workflows, [], None)

    def test_display_status_missing_task_groups(self):
        """Test displaying jobs with missing task groups."""
        jobs = [
            {
                "name": "projects/p/locations/l/jobs/runner-job",
                "status": {"state": "QUEUED"},
                "labels": {"stage": "runner"},
            }
        ]
        # Should handle gracefully
        display_status([], jobs, None)


class TestStatusWatchMode:
    """Test status watch mode."""

    @patch("epycloud.commands.status.handlers.fetch_active_batch_jobs")
    @patch("epycloud.commands.status.handlers.fetch_active_workflows")
    @patch("epycloud.commands.status.handlers.time.sleep")
    @patch("epycloud.commands.status.handlers.get_google_cloud_config")
    @patch("epycloud.commands.status.handlers.require_config")
    def test_status_watch_mode_interrupt(
        self,
        mock_require_config,
        mock_gcloud_config,
        mock_sleep,
        mock_fetch_workflows,
        mock_fetch_jobs,
        mock_config,
    ):
        """Test watch mode with keyboard interrupt."""
        mock_require_config.return_value = mock_config
        mock_gcloud_config.return_value = {
            "project_id": "test-project",
            "region": "us-central1",
        }
        mock_fetch_workflows.return_value = []
        mock_fetch_jobs.return_value = []
        # Simulate Ctrl+C after first iteration
        mock_sleep.side_effect = KeyboardInterrupt()

        args = Mock(watch=True, exp_id=None, interval=10)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = status.handle(ctx)

        assert exit_code == 0


class TestStatusMissingConfig:
    """Test status command with missing configuration."""

    @patch("epycloud.lib.command_helpers.require_config")
    def test_status_missing_config(self, mock_require_config):
        """Test error when config is missing."""
        from epycloud.exceptions import ConfigError

        mock_require_config.side_effect = ConfigError("Config not found")

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(watch=False, exp_id=None, interval=10),
        }

        exit_code = status.handle(ctx)

        assert exit_code == 2

    @patch("epycloud.commands.status.handlers.get_google_cloud_config")
    @patch("epycloud.commands.status.handlers.require_config")
    def test_status_missing_project_id(self, mock_require_config, mock_gcloud_config, mock_config):
        """Test error when project_id is missing."""
        mock_require_config.return_value = mock_config
        mock_gcloud_config.side_effect = KeyError("project_id")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(watch=False, exp_id=None, interval=10),
        }

        exit_code = status.handle(ctx)

        assert exit_code == 2
