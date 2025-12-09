"""Integration tests for cloud job submission.

Tests use minimal mocking - only external boundaries (gcloud subprocess calls).
Internal validation logic and batch config building use real implementations.
"""

import json
import tempfile
from argparse import Namespace
from unittest.mock import Mock, patch

from epycloud.commands import run


class TestRunJobCloud:
    """Test run job command for cloud execution."""

    @patch("epycloud.commands.run.cloud.job.subprocess.run")
    def test_run_job_stage_a_cloud_success(self, mock_subprocess, mock_config):
        """Test successful Stage A job submission to cloud."""
        # Mock gcloud batch submit success
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="A",
                exp_id="test-sim",
                run_id=None,  # Auto-generated for stage A
                task_index=0,
                num_tasks=None,
                output_config=None,
                local=False,  # Cloud mode
                machine_type=None,
                task_count_per_node=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should succeed
        assert exit_code == 0
        # gcloud batch jobs submit should be called
        assert mock_subprocess.called
        call_args = mock_subprocess.call_args[0][0]
        assert "gcloud" in call_args
        assert "batch" in call_args
        assert "jobs" in call_args
        assert "submit" in call_args

    @patch("epycloud.commands.run.cloud.job.subprocess.run")
    def test_run_job_stage_b_cloud_success(self, mock_subprocess, mock_config):
        """Test successful Stage B job submission to cloud."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="B",
                exp_id="test-sim",
                run_id="20251107-100000-abc12345",
                task_index=5,  # Specific task
                num_tasks=None,
                output_config=None,
                local=False,
                machine_type=None,
                task_count_per_node=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called

    @patch("epycloud.commands.run.cloud.job.subprocess.run")
    def test_run_job_stage_c_cloud_success(self, mock_subprocess, mock_config):
        """Test successful Stage C job submission to cloud."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="C",
                exp_id="test-sim",
                run_id="20251107-100000-abc12345",
                task_index=0,
                num_tasks=10,  # Required for stage C
                output_config=None,
                local=False,
                machine_type=None,
                task_count_per_node=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called

    @patch("epycloud.commands.run.cloud.job.subprocess.run")
    def test_run_job_cloud_with_output_config(self, mock_subprocess, mock_config):
        """Test Stage C job with specific output config."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="C",
                exp_id="test-sim",
                run_id="20251107-100000-abc12345",
                task_index=0,
                num_tasks=10,
                output_config="output_projection.yaml",
                local=False,
                machine_type=None,
                task_count_per_node=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called

    @patch("epycloud.commands.run.cloud.job.subprocess.run")
    def test_run_job_cloud_submission_failure(self, mock_subprocess, mock_config):
        """Test error handling when gcloud batch submit fails."""
        # Mock gcloud failure
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="Error submitting job")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="A",
                exp_id="test-sim",
                run_id=None,
                task_index=0,
                num_tasks=None,
                output_config=None,
                local=False,
                machine_type=None,
                task_count_per_node=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should fail
        assert exit_code == 1
        assert mock_subprocess.called

    def test_run_job_cloud_missing_project_id(self):
        """Test error when project_id is missing from config."""
        # Config without google_cloud section
        invalid_config = {
            "docker": {
                "repo_name": "test-repo",
                "image_name": "test-image",
                "image_tag": "latest",
            },
            "github": {
                "forecast_repo": "owner/repo",
            },
        }

        ctx = {
            "config": invalid_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="A",
                exp_id="test-sim",
                run_id=None,
                task_index=0,
                num_tasks=None,
                output_config=None,
                local=False,
                machine_type=None,
                task_count_per_node=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should fail with config error
        assert exit_code == 2

    def test_run_job_cloud_missing_bucket_name(self):
        """Test error when bucket_name is missing from config."""
        invalid_config = {
            "google_cloud": {
                "project_id": "test-project",
                "region": "us-central1",
                # Missing bucket_name
            },
            "docker": {
                "repo_name": "test-repo",
                "image_name": "test-image",
                "image_tag": "latest",
            },
            "github": {
                "forecast_repo": "owner/repo",
            },
            "batch": {},
        }

        ctx = {
            "config": invalid_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="A",
                exp_id="test-sim",
                run_id=None,
                task_index=0,
                num_tasks=None,
                output_config=None,
                local=False,
                machine_type=None,
                task_count_per_node=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should fail with config error
        assert exit_code == 2

    def test_run_job_cloud_dry_run_mode(self, mock_config):
        """Test dry run mode doesn't submit actual job."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": True,  # Dry run mode
            "args": Namespace(
                run_subcommand="job",
                stage="A",
                exp_id="test-sim",
                run_id=None,
                task_index=0,
                num_tasks=None,
                output_config=None,
                local=False,
                machine_type=None,
                task_count_per_node=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should succeed (dry run shows config but doesn't submit)
        assert exit_code == 0

    @patch("epycloud.commands.run.cloud.job.subprocess.run")
    def test_run_job_cloud_with_task_count_per_node(self, mock_subprocess, mock_config):
        """Test job submission with custom task_count_per_node."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="A",
                exp_id="test-sim",
                run_id=None,
                task_index=0,
                num_tasks=None,
                output_config=None,
                local=False,
                machine_type=None,
                task_count_per_node=4,  # Custom value
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called


class TestRunJobCloudMachineType:
    """Test machine type override for cloud job submission."""

    @patch("epycloud.lib.validation.subprocess.run")
    def test_run_job_cloud_with_machine_type_override(self, mock_subprocess, mock_config):
        """Test job submission with machine type override."""
        # Mock machine type validation and job submission
        def subprocess_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            cmd_str = " ".join(cmd)

            if "machine-types describe" in cmd_str:
                # Return machine specs
                return Mock(
                    returncode=0,
                    stdout=json.dumps({"guestCpus": 8, "memoryMb": 32768, "name": "c2-standard-8"}),
                    stderr="",
                )
            elif "machine-types list" in cmd_str:
                return Mock(returncode=0, stdout="c2-standard-8\nn2-standard-4\n", stderr="")
            elif "batch" in cmd_str and "jobs" in cmd_str and "submit" in cmd_str:
                # Job submission
                return Mock(returncode=0, stdout="", stderr="")
            return Mock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = subprocess_side_effect

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="A",
                exp_id="test-sim",
                run_id=None,
                task_index=0,
                num_tasks=None,
                output_config=None,
                local=False,
                machine_type="c2-standard-8",  # Override
                task_count_per_node=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should succeed
        assert exit_code == 0
        assert mock_subprocess.called

    @patch("epycloud.lib.validation.subprocess.run")
    def test_run_job_cloud_with_invalid_machine_type(self, mock_subprocess, mock_config):
        """Test job submission fails with invalid machine type."""
        # Mock machine type not found
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="A",
                exp_id="test-sim",
                run_id=None,
                task_index=0,
                num_tasks=None,
                output_config=None,
                local=False,
                machine_type="invalid-machine-type",
                task_count_per_node=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should fail with validation error
        assert exit_code == 1


