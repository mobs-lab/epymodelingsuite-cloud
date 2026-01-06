"""Integration tests for workflow command."""

import json
from unittest.mock import Mock, call, patch

import pytest
import requests

from epycloud.commands import workflow


class TestWorkflowListCommand:
    """Test workflow list command."""

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_list_success(self, mock_get, mock_token, mock_config):
        """Test successful listing of workflow executions."""
        mock_token.return_value = "test-token"

        # Mock list response
        list_response = Mock()
        list_response.json.return_value = {
            "executions": [
                {
                    "name": "projects/test-project/locations/us-central1/"
                    "workflows/epymodelingsuite-pipeline/executions/exec-123",
                    "state": "SUCCEEDED",
                    "startTime": "2025-11-16T10:00:00Z",
                },
                {
                    "name": "projects/test-project/locations/us-central1/"
                    "workflows/epymodelingsuite-pipeline/executions/exec-456",
                    "state": "ACTIVE",
                    "startTime": "2025-11-16T11:00:00Z",
                },
            ]
        }
        list_response.raise_for_status = Mock()

        # Mock describe responses for enrichment
        describe_response_1 = Mock()
        describe_response_1.json.return_value = {
            "argument": json.dumps({"exp_id": "test-exp-1"})
        }
        describe_response_1.raise_for_status = Mock()

        describe_response_2 = Mock()
        describe_response_2.json.return_value = {
            "argument": json.dumps({"exp_id": "test-exp-2"})
        }
        describe_response_2.raise_for_status = Mock()

        # Setup mock to return different responses for list vs describe
        mock_get.side_effect = [
            list_response,
            describe_response_1,
            describe_response_2,
        ]

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="list",
                limit=20,
                status=None,
                exp_id=None,
                since=None,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 0
        assert mock_get.called
        assert mock_token.called

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_list_with_status_filter(self, mock_get, mock_token, mock_config):
        """Test listing with status filter."""
        mock_token.return_value = "test-token"

        list_response = Mock()
        list_response.json.return_value = {"executions": []}
        list_response.raise_for_status = Mock()
        mock_get.return_value = list_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="list",
                limit=10,
                status="FAILED",
                exp_id=None,
                since=None,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 0
        # Check that filter was included in URL
        call_args = mock_get.call_args
        assert 'filter=state="FAILED"' in call_args[0][0]

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_list_with_exp_id_filter(self, mock_get, mock_token, mock_config):
        """Test listing with exp_id filter."""
        mock_token.return_value = "test-token"

        list_response = Mock()
        list_response.json.return_value = {
            "executions": [
                {
                    "name": "projects/test-project/locations/us-central1/"
                    "workflows/epymodelingsuite-pipeline/executions/exec-123",
                    "state": "SUCCEEDED",
                    "startTime": "2025-11-16T10:00:00Z",
                }
            ]
        }
        list_response.raise_for_status = Mock()

        describe_response = Mock()
        describe_response.json.return_value = {
            "argument": json.dumps({"exp_id": "target-exp"})
        }
        describe_response.raise_for_status = Mock()

        mock_get.side_effect = [list_response, describe_response]

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="list",
                limit=20,
                status=None,
                exp_id="target-exp",
                since=None,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_list_empty_result(self, mock_get, mock_token, mock_config):
        """Test handling when no executions found."""
        mock_token.return_value = "test-token"

        list_response = Mock()
        list_response.json.return_value = {"executions": []}
        list_response.raise_for_status = Mock()
        mock_get.return_value = list_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="list",
                limit=20,
                status=None,
                exp_id=None,
                since=None,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_list_api_error(self, mock_get, mock_token, mock_config):
        """Test handling of API errors."""
        mock_token.return_value = "test-token"

        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        http_error = requests.HTTPError()
        http_error.response = error_response
        error_response.raise_for_status = Mock(side_effect=http_error)
        mock_get.return_value = error_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="list",
                limit=20,
                status=None,
                exp_id=None,
                since=None,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1

    def test_workflow_list_missing_project_id(self):
        """Test error when project_id is not configured."""
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
                workflow_subcommand="list",
                limit=20,
                status=None,
                exp_id=None,
                since=None,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 2  # Config error


class TestWorkflowDescribeCommand:
    """Test workflow describe command."""

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_describe_success(self, mock_get, mock_token, mock_config):
        """Test successful describe of workflow execution."""
        mock_token.return_value = "test-token"

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/exec-123",
            "state": "SUCCEEDED",
            "startTime": "2025-11-16T10:00:00Z",
            "endTime": "2025-11-16T11:00:00Z",
            "argument": json.dumps({"exp_id": "test-exp"}),
            "result": json.dumps({"status": "completed"}),
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="describe",
                execution_id="exec-123",
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 0
        assert mock_get.called

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_describe_not_found(self, mock_get, mock_token, mock_config):
        """Test handling of 404 for unknown execution."""
        mock_token.return_value = "test-token"

        error_response = Mock()
        error_response.status_code = 404
        error_response.text = "Not Found"
        http_error = requests.HTTPError()
        http_error.response = error_response
        error_response.raise_for_status = Mock(side_effect=http_error)
        mock_get.return_value = error_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="describe",
                execution_id="nonexistent-exec",
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_describe_with_full_name(self, mock_get, mock_token, mock_config):
        """Test describe with full execution name."""
        mock_token.return_value = "test-token"

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/exec-123",
            "state": "ACTIVE",
            "startTime": "2025-11-16T10:00:00Z",
            "argument": "{}",
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="describe",
                execution_id="projects/test-project/locations/us-central1/"
                "workflows/epymodelingsuite-pipeline/executions/exec-123",
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 0


class TestWorkflowCancelCommand:
    """Test workflow cancel command."""

    @patch("epycloud.commands.workflow.api.list_batch_jobs_for_run")
    @patch("epycloud.commands.workflow.api.get_execution")
    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    def test_workflow_cancel_success(
        self, mock_post, mock_token, mock_get_exec, mock_list_jobs, mock_config
    ):
        """Test successful cancellation of running workflow."""
        mock_token.return_value = "test-token"

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Mock execution with run_id
        mock_get_exec.return_value = {
            "name": "projects/test/locations/us-central1/workflows/epymodelingsuite-pipeline/executions/exec-123",
            "argument": json.dumps({"run_id": "20251210-120000-abcd1234", "exp_id": "test-exp"}),
        }

        # Mock empty list of batch jobs
        mock_list_jobs.return_value = []

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 0
        assert mock_post.called
        # Verify cancel URL
        call_args = mock_post.call_args
        assert ":cancel" in call_args[0][0]

    @patch("epycloud.commands.workflow.api.list_batch_jobs_for_run")
    @patch("epycloud.commands.workflow.api.get_execution")
    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    def test_workflow_cancel_already_done(
        self, mock_post, mock_token, mock_get_exec, mock_list_jobs, mock_config
    ):
        """Test canceling already completed workflow."""
        mock_token.return_value = "test-token"

        # Mock execution with run_id
        mock_get_exec.return_value = {
            "name": "projects/test/locations/us-central1/workflows/epymodelingsuite-pipeline/executions/exec-123",
            "argument": json.dumps({"run_id": "20251210-120000-abcd1234", "exp_id": "test-exp"}),
        }

        # Mock empty list of batch jobs
        mock_list_jobs.return_value = []

        error_response = Mock()
        error_response.status_code = 400
        error_response.text = "Execution already completed"
        http_error = requests.HTTPError()
        http_error.response = error_response
        error_response.raise_for_status = Mock(side_effect=http_error)
        mock_post.return_value = error_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1

    def test_workflow_cancel_dry_run(self, mock_config):
        """Test cancel dry run mode."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 0


class TestWorkflowRetryCommand:
    """Test workflow retry command."""

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_retry_success(self, mock_get, mock_post, mock_token, mock_config):
        """Test successful retry of failed workflow."""
        mock_token.return_value = "test-token"

        # Mock get for fetching original execution
        get_response = Mock()
        get_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/failed-exec",
            "state": "FAILED",
            "argument": json.dumps({"exp_id": "test-exp", "run_id": "run-123"}),
        }
        get_response.raise_for_status = Mock()
        mock_get.return_value = get_response

        # Mock post for submitting new execution
        post_response = Mock()
        post_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/new-exec"
        }
        post_response.raise_for_status = Mock()
        mock_post.return_value = post_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="retry",
                execution_id="failed-exec",
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 0
        assert mock_get.called
        assert mock_post.called
        # Verify same arguments were used
        post_call_args = mock_post.call_args
        submitted_arg = json.loads(post_call_args[1]["json"]["argument"])
        assert submitted_arg["exp_id"] == "test-exp"

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_retry_not_found(self, mock_get, mock_token, mock_config):
        """Test retry of non-existent execution."""
        mock_token.return_value = "test-token"

        error_response = Mock()
        error_response.status_code = 404
        error_response.text = "Not Found"
        http_error = requests.HTTPError()
        http_error.response = error_response
        error_response.raise_for_status = Mock(side_effect=http_error)
        mock_get.return_value = error_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="retry",
                execution_id="nonexistent-exec",
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_retry_dry_run(self, mock_get, mock_token, mock_config):
        """Test retry dry run mode."""
        mock_token.return_value = "test-token"

        get_response = Mock()
        get_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/failed-exec",
            "state": "FAILED",
            "argument": json.dumps({"exp_id": "test-exp"}),
        }
        get_response.raise_for_status = Mock()
        mock_get.return_value = get_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(
                workflow_subcommand="retry",
                execution_id="failed-exec",
            ),
        }

        with patch("epycloud.commands.workflow.api.requests.post") as mock_post:
            exit_code = workflow.handle(ctx)

            assert exit_code == 0
            # Should not make post request in dry run
            assert not mock_post.called


class TestWorkflowLogsCommand:
    """Test workflow logs command."""

    @patch("epycloud.commands.workflow.streaming.subprocess.run")
    def test_workflow_logs_success(self, mock_subprocess, mock_config):
        """Test fetching workflow logs."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "timestamp": "2025-11-16T10:00:00Z",
                        "severity": "INFO",
                        "textPayload": "Workflow started",
                    },
                    {
                        "timestamp": "2025-11-16T10:01:00Z",
                        "severity": "INFO",
                        "textPayload": "Stage A completed",
                    },
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
                workflow_subcommand="logs",
                execution_id="exec-123",
                follow=False,
                tail=100,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called

    @patch("epycloud.commands.workflow.streaming.subprocess.run")
    def test_workflow_logs_empty(self, mock_subprocess, mock_config):
        """Test handling empty logs."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="logs",
                execution_id="exec-123",
                follow=False,
                tail=100,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.workflow.streaming.subprocess.run")
    def test_workflow_logs_gcloud_error(self, mock_subprocess, mock_config):
        """Test handling gcloud command failure."""
        from subprocess import CalledProcessError

        mock_subprocess.side_effect = CalledProcessError(
            returncode=1, cmd=["gcloud", "logging", "read"], stderr="Permission denied"
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="logs",
                execution_id="exec-123",
                follow=False,
                tail=100,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1


class TestWorkflowHelperFunctions:
    """Test workflow helper functions."""

    def test_parse_execution_name_short_id(self):
        """Test parsing short execution ID."""
        result = workflow.api.parse_execution_name(
            "exec-123", "my-project", "us-central1", "my-workflow"
        )
        expected = (
            "projects/my-project/locations/us-central1/workflows/my-workflow/executions/exec-123"
        )
        assert result == expected

    def test_parse_execution_name_full_path(self):
        """Test parsing full execution path."""
        full_path = "projects/p/locations/l/workflows/w/executions/e"
        result = workflow.api.parse_execution_name(full_path, "x", "y", "z")
        assert result == full_path

    def test_parse_timestamp_utc(self):
        """Test parsing UTC timestamp."""
        ts = "2025-11-16T10:00:00Z"
        result = workflow.handlers._parse_timestamp(ts)
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 16

    def test_parse_timestamp_with_offset(self):
        """Test parsing timestamp with offset."""
        ts = "2025-11-16T10:00:00+00:00"
        result = workflow.handlers._parse_timestamp(ts)
        assert result.year == 2025

    def test_parse_timestamp_invalid(self):
        """Test parsing invalid timestamp."""
        result = workflow.handlers._parse_timestamp("invalid")
        from datetime import datetime

        assert result == datetime.min.replace(tzinfo=result.tzinfo)


class TestWorkflowNoSubcommand:
    """Test workflow command without subcommand."""

    def test_workflow_no_subcommand(self, mock_config):
        """Test error when no subcommand specified."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand=None,
                _workflow_parser=Mock(print_help=Mock()),
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1

    def test_workflow_missing_config(self):
        """Test error when config is missing."""
        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "dry_run": False,
            "args": Mock(workflow_subcommand="list"),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 2


class TestWorkflowListErrorPaths:
    """Test error handling in workflow list command."""

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_list_network_error(self, mock_get, mock_token, mock_config):
        """Test handling of network errors during list."""
        mock_token.return_value = "test-token"
        mock_get.side_effect = requests.ConnectionError("Network unreachable")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="list",
                limit=20,
                status=None,
                exp_id=None,
                since=None,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_list_json_decode_error(self, mock_get, mock_token, mock_config):
        """Test handling of malformed JSON responses."""
        mock_token.return_value = "test-token"

        # Mock response with malformed JSON
        error_response = Mock()
        error_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        error_response.raise_for_status = Mock()
        mock_get.return_value = error_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="list",
                limit=20,
                status=None,
                exp_id=None,
                since=None,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_list_enrichment_failure(self, mock_get, mock_token, mock_config):
        """Test handling when enrichment (describe) calls fail for some executions."""
        mock_token.return_value = "test-token"

        # Mock list response
        list_response = Mock()
        list_response.json.return_value = {
            "executions": [
                {
                    "name": "projects/test-project/locations/us-central1/"
                    "workflows/epymodelingsuite-pipeline/executions/exec-123",
                    "state": "SUCCEEDED",
                    "startTime": "2025-11-16T10:00:00Z",
                },
            ]
        }
        list_response.raise_for_status = Mock()

        # Mock describe failure (404)
        error_response = Mock()
        error_response.status_code = 404
        http_error = requests.HTTPError()
        http_error.response = error_response
        error_response.raise_for_status = Mock(side_effect=http_error)

        mock_get.side_effect = [list_response, error_response]

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="list",
                limit=20,
                status=None,
                exp_id=None,
                since=None,
            ),
        }

        exit_code = workflow.handle(ctx)

        # Should still succeed (show executions without enrichment)
        assert exit_code == 0


class TestWorkflowCancelErrorPaths:
    """Test error handling in workflow cancel command."""

    @patch("epycloud.commands.workflow.api.get_execution")
    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    def test_workflow_cancel_network_error(
        self, mock_post, mock_token, mock_get_exec, mock_config
    ):
        """Test handling of network errors during cancel."""
        mock_token.return_value = "test-token"

        # Mock execution with run_id
        mock_get_exec.return_value = {
            "name": "projects/test/locations/us-central1/workflows/epymodelingsuite-pipeline/executions/exec-123",
            "argument": json.dumps({"run_id": "20251210-120000-abcd1234", "exp_id": "test-exp"}),
        }

        mock_post.side_effect = requests.ConnectionError("Network unreachable")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.workflow.api.get_execution")
    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    def test_workflow_cancel_not_found(
        self, mock_post, mock_token, mock_get_exec, mock_config
    ):
        """Test canceling non-existent workflow."""
        mock_token.return_value = "test-token"

        # Mock 404 from get_execution
        error_response = Mock()
        error_response.status_code = 404
        error_response.text = "Execution not found"
        http_error = requests.HTTPError()
        http_error.response = error_response
        mock_get_exec.side_effect = http_error

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="nonexistent-exec",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1


class TestWorkflowCancelWithBatchJobs:
    """Test workflow cancel with batch job cascade cancellation."""

    @patch("epycloud.commands.workflow.api.cancel_batch_job")
    @patch("epycloud.commands.workflow.api.list_batch_jobs_for_run")
    @patch("epycloud.commands.workflow.api.get_execution")
    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    def test_cancel_with_batch_jobs_cascade(
        self,
        mock_post,
        mock_token,
        mock_get_exec,
        mock_list_jobs,
        mock_cancel_job,
        mock_config,
    ):
        """Test canceling workflow with active batch jobs (default cascade behavior)."""
        mock_token.return_value = "test-token"

        # Mock successful workflow cancel
        mock_cancel_response = Mock()
        mock_cancel_response.status_code = 200
        mock_cancel_response.json.return_value = {"name": "test-execution"}
        mock_post.return_value = mock_cancel_response

        # Mock execution with run_id
        mock_get_exec.return_value = {
            "name": "projects/test/locations/us-central1/workflows/epymodelingsuite-pipeline/executions/exec-123",
            "argument": json.dumps({"run_id": "20251210-120000-abcd1234", "exp_id": "test-exp"}),
        }

        # Mock 3 active batch jobs
        mock_list_jobs.return_value = [
            {
                "name": "projects/test/locations/us-central1/jobs/builder-job",
                "labels": {"stage": "builder", "run_id": "20251210-120000-abcd1234"},
            },
            {
                "name": "projects/test/locations/us-central1/jobs/runner-job",
                "labels": {"stage": "runner", "run_id": "20251210-120000-abcd1234"},
            },
            {
                "name": "projects/test/locations/us-central1/jobs/output-job",
                "labels": {"stage": "output", "run_id": "20251210-120000-abcd1234"},
            },
        ]

        # Mock successful batch job cancellation
        mock_cancel_job.return_value = {"name": "job-cancelled"}

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        # Verify workflow was cancelled
        assert exit_code == 0
        assert mock_post.call_count == 1

        # Verify execution details were fetched
        assert mock_get_exec.call_count == 1

        # Verify batch jobs were listed
        assert mock_list_jobs.call_count == 1
        mock_list_jobs.assert_called_with("test-project", "us-central1", "20251210-120000-abcd1234", False)

        # Verify all 3 batch jobs were cancelled
        assert mock_cancel_job.call_count == 3

    @patch("epycloud.commands.workflow.api.list_batch_jobs_for_run")
    @patch("epycloud.commands.workflow.api.get_execution")
    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    def test_cancel_only_workflow_flag(
        self, mock_post, mock_token, mock_get_exec, mock_list_jobs, mock_config
    ):
        """Test --only-workflow flag prevents batch job cancellation."""
        mock_token.return_value = "test-token"

        # Mock successful workflow cancel
        mock_cancel_response = Mock()
        mock_cancel_response.status_code = 200
        mock_cancel_response.json.return_value = {"name": "test-execution"}
        mock_post.return_value = mock_cancel_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=True,
            ),
        }

        exit_code = workflow.handle(ctx)

        # Verify workflow was cancelled
        assert exit_code == 0
        assert mock_post.call_count == 1

        # Verify execution details were NOT fetched
        assert mock_get_exec.call_count == 0

        # Verify batch jobs were NOT listed
        assert mock_list_jobs.call_count == 0

    @patch("epycloud.commands.workflow.api.list_batch_jobs_for_run")
    @patch("epycloud.commands.workflow.api.get_execution")
    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    def test_cancel_no_run_id_in_execution(
        self, mock_post, mock_token, mock_get_exec, mock_list_jobs, mock_config
    ):
        """Test cancellation when execution has no run_id."""
        mock_token.return_value = "test-token"

        # Mock successful workflow cancel
        mock_cancel_response = Mock()
        mock_cancel_response.status_code = 200
        mock_cancel_response.json.return_value = {"name": "test-execution"}
        mock_post.return_value = mock_cancel_response

        # Mock execution without run_id
        mock_get_exec.return_value = {
            "name": "projects/test/locations/us-central1/workflows/epymodelingsuite-pipeline/executions/exec-123",
            "argument": json.dumps({"exp_id": "test-exp"}),  # No run_id
        }

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        # Verify workflow was cancelled successfully
        assert exit_code == 0

        # Verify execution details were fetched
        assert mock_get_exec.call_count == 1

        # Verify batch jobs were NOT listed (no run_id)
        assert mock_list_jobs.call_count == 0

    @patch("epycloud.commands.workflow.api.list_batch_jobs_for_run")
    @patch("epycloud.commands.workflow.api.get_execution")
    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    def test_cancel_no_batch_jobs_found(
        self, mock_post, mock_token, mock_get_exec, mock_list_jobs, mock_config
    ):
        """Test cancellation when no active batch jobs exist."""
        mock_token.return_value = "test-token"

        # Mock successful workflow cancel
        mock_cancel_response = Mock()
        mock_cancel_response.status_code = 200
        mock_cancel_response.json.return_value = {"name": "test-execution"}
        mock_post.return_value = mock_cancel_response

        # Mock execution with run_id
        mock_get_exec.return_value = {
            "name": "projects/test/locations/us-central1/workflows/epymodelingsuite-pipeline/executions/exec-123",
            "argument": json.dumps({"run_id": "20251210-120000-abcd1234", "exp_id": "test-exp"}),
        }

        # Mock empty list of batch jobs
        mock_list_jobs.return_value = []

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        # Verify success
        assert exit_code == 0

        # Verify batch jobs were listed
        assert mock_list_jobs.call_count == 1

    @patch("epycloud.commands.workflow.api.cancel_batch_job")
    @patch("epycloud.commands.workflow.api.list_batch_jobs_for_run")
    @patch("epycloud.commands.workflow.api.get_execution")
    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    def test_cancel_partial_batch_failure(
        self,
        mock_post,
        mock_token,
        mock_get_exec,
        mock_list_jobs,
        mock_cancel_job,
        mock_config,
    ):
        """Test cancellation when some batch jobs fail to cancel."""
        mock_token.return_value = "test-token"

        # Mock successful workflow cancel
        mock_cancel_response = Mock()
        mock_cancel_response.status_code = 200
        mock_cancel_response.json.return_value = {"name": "test-execution"}
        mock_post.return_value = mock_cancel_response

        # Mock execution with run_id
        mock_get_exec.return_value = {
            "name": "projects/test/locations/us-central1/workflows/epymodelingsuite-pipeline/executions/exec-123",
            "argument": json.dumps({"run_id": "20251210-120000-abcd1234", "exp_id": "test-exp"}),
        }

        # Mock 3 batch jobs
        mock_list_jobs.return_value = [
            {
                "name": "projects/test/locations/us-central1/jobs/job1",
                "labels": {"stage": "builder", "run_id": "20251210-120000-abcd1234"},
            },
            {
                "name": "projects/test/locations/us-central1/jobs/job2",
                "labels": {"stage": "runner", "run_id": "20251210-120000-abcd1234"},
            },
            {
                "name": "projects/test/locations/us-central1/jobs/job3",
                "labels": {"stage": "output", "run_id": "20251210-120000-abcd1234"},
            },
        ]

        # Mock: first two succeed, third fails with HTTP 500
        error_response = Mock()
        error_response.status_code = 500
        http_error = requests.HTTPError()
        http_error.response = error_response

        mock_cancel_job.side_effect = [
            {"name": "job1-cancelled"},
            {"name": "job2-cancelled"},
            http_error,
        ]

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        # Verify workflow was still cancelled successfully
        assert exit_code == 0

        # Verify all 3 batch jobs were attempted
        assert mock_cancel_job.call_count == 3

    @patch("epycloud.commands.workflow.api.cancel_batch_job")
    @patch("epycloud.commands.workflow.api.list_batch_jobs_for_run")
    @patch("epycloud.commands.workflow.api.get_execution")
    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    def test_cancel_batch_job_already_done(
        self,
        mock_post,
        mock_token,
        mock_get_exec,
        mock_list_jobs,
        mock_cancel_job,
        mock_config,
    ):
        """Test cancellation when batch job is already completed."""
        mock_token.return_value = "test-token"

        # Mock successful workflow cancel
        mock_cancel_response = Mock()
        mock_cancel_response.status_code = 200
        mock_cancel_response.json.return_value = {"name": "test-execution"}
        mock_post.return_value = mock_cancel_response

        # Mock execution with run_id
        mock_get_exec.return_value = {
            "name": "projects/test/locations/us-central1/workflows/epymodelingsuite-pipeline/executions/exec-123",
            "argument": json.dumps({"run_id": "20251210-120000-abcd1234", "exp_id": "test-exp"}),
        }

        # Mock 1 batch job
        mock_list_jobs.return_value = [
            {
                "name": "projects/test/locations/us-central1/jobs/job1",
                "labels": {"stage": "builder", "run_id": "20251210-120000-abcd1234"},
            }
        ]

        # Mock HTTP 400 (already completed)
        error_response = Mock()
        error_response.status_code = 400
        http_error = requests.HTTPError()
        http_error.response = error_response
        mock_cancel_job.side_effect = http_error

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        # Verify success (HTTP 400 treated as info, not error)
        assert exit_code == 0

    @patch("epycloud.commands.workflow.api.list_batch_jobs_for_run")
    @patch("epycloud.commands.workflow.api.get_execution")
    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    def test_cancel_execution_fetch_fails(
        self, mock_post, mock_token, mock_get_exec, mock_list_jobs, mock_config
    ):
        """Test cancellation when execution details cannot be fetched."""
        mock_token.return_value = "test-token"

        # Mock execution fetch failure with HTTP 500
        error_response = Mock()
        error_response.status_code = 500
        http_error = requests.HTTPError()
        http_error.response = error_response
        mock_get_exec.side_effect = http_error

        # Mock successful workflow cancel
        mock_cancel_response = Mock()
        mock_cancel_response.status_code = 200
        mock_cancel_response.json.return_value = {"name": "test-execution"}
        mock_post.return_value = mock_cancel_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        # Verify workflow was still cancelled successfully
        assert exit_code == 0

        # Verify batch jobs were NOT listed (couldn't get run_id)
        assert mock_list_jobs.call_count == 0

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    def test_cancel_dry_run_with_cascade(self, mock_token, mock_config):
        """Test dry run doesn't actually cancel anything."""
        mock_token.return_value = "test-token"

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(
                workflow_subcommand="cancel",
                execution_id="exec-123",
                only_workflow=False,
            ),
        }

        exit_code = workflow.handle(ctx)

        # Verify success
        assert exit_code == 0

        # Verify no token was actually used (dry run exits early)
        assert mock_token.call_count == 0


class TestWorkflowRetryErrorPaths:
    """Test error handling in workflow retry command."""

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_retry_malformed_argument(self, mock_get, mock_token, mock_config):
        """Test retry when original execution has malformed argument."""
        mock_token.return_value = "test-token"

        get_response = Mock()
        get_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/failed-exec",
            "state": "FAILED",
            "argument": "not-valid-json",  # Malformed JSON
        }
        get_response.raise_for_status = Mock()
        mock_get.return_value = get_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="retry",
                execution_id="failed-exec",
            ),
        }

        exit_code = workflow.handle(ctx)

        # Should fail gracefully
        assert exit_code == 1

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.post")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_retry_submission_failure(self, mock_get, mock_post, mock_token, mock_config):
        """Test retry when new submission fails."""
        mock_token.return_value = "test-token"

        # Mock get for fetching original execution
        get_response = Mock()
        get_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/failed-exec",
            "state": "FAILED",
            "argument": json.dumps({"exp_id": "test-exp", "run_id": "run-123"}),
        }
        get_response.raise_for_status = Mock()
        mock_get.return_value = get_response

        # Mock post failure
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        http_error = requests.HTTPError()
        http_error.response = error_response
        error_response.raise_for_status = Mock(side_effect=http_error)
        mock_post.return_value = error_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="retry",
                execution_id="failed-exec",
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_retry_network_error(self, mock_get, mock_token, mock_config):
        """Test retry with network error."""
        mock_token.return_value = "test-token"
        mock_get.side_effect = requests.ConnectionError("Network unreachable")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="retry",
                execution_id="failed-exec",
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1


class TestWorkflowDescribeErrorPaths:
    """Test error handling in workflow describe command."""

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_describe_network_error(self, mock_get, mock_token, mock_config):
        """Test describe with network error."""
        mock_token.return_value = "test-token"
        mock_get.side_effect = requests.ConnectionError("Network unreachable")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="describe",
                execution_id="exec-123",
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.workflow.handlers.get_gcloud_access_token")
    @patch("epycloud.commands.workflow.api.requests.get")
    def test_workflow_describe_malformed_json(self, mock_get, mock_token, mock_config):
        """Test describe with malformed JSON response."""
        mock_token.return_value = "test-token"

        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                workflow_subcommand="describe",
                execution_id="exec-123",
            ),
        }

        exit_code = workflow.handle(ctx)

        assert exit_code == 1


class TestWorkflowExecutionNameParsing:
    """Test execution name parsing edge cases."""

    def test_parse_execution_name_with_special_chars(self):
        """Test parsing execution ID with special characters."""
        result = workflow.api.parse_execution_name(
            "exec-123-abc_def", "my-project", "us-central1", "my-workflow"
        )
        expected = (
            "projects/my-project/locations/us-central1/workflows/"
            "my-workflow/executions/exec-123-abc_def"
        )
        assert result == expected

    def test_parse_execution_name_empty_id(self):
        """Test parsing empty execution ID."""
        result = workflow.api.parse_execution_name("", "my-project", "us-central1", "my-workflow")
        expected = "projects/my-project/locations/us-central1/workflows/my-workflow/executions/"
        assert result == expected

    def test_parse_execution_name_partial_path(self):
        """Test parsing partial path (should treat as short ID)."""
        partial = "workflows/my-workflow/executions/exec-123"
        result = workflow.api.parse_execution_name(partial, "p", "us-central1", "w")
        # Should treat as short ID since it doesn't start with "projects/"
        expected = f"projects/p/locations/us-central1/workflows/w/executions/{partial}"
        assert result == expected


class TestListBatchJobsForRun:
    """Test list_batch_jobs_for_run filter format."""

    @patch("subprocess.run")
    def test_list_batch_jobs_filter_format(self, mock_subprocess):
        """Test that gcloud filter uses quotes around label values."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps([]),
            stderr="",
        )

        from epycloud.commands.workflow.api import list_batch_jobs_for_run

        list_batch_jobs_for_run("test-project", "us-central1", "20251210-120000-abcd1234", False)

        # Verify gcloud command was called with correct filter format
        cmd = mock_subprocess.call_args[0][0]

        # Find the filter argument (it's in format --filter=value)
        filter_arg = None
        for arg in cmd:
            if arg.startswith("--filter="):
                filter_arg = arg.split("=", 1)[1]
                break

        assert filter_arg is not None, "Filter argument not found in gcloud command"

        # Verify label value is quoted
        assert 'labels.run_id="20251210-120000-abcd1234"' in filter_arg

        # Verify state filter is present
        assert "status.state:RUNNING" in filter_arg
        assert "status.state:QUEUED" in filter_arg
        assert "status.state:SCHEDULED" in filter_arg
