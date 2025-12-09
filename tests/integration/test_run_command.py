"""Integration tests for run command.

Tests use minimal mocking - only external boundaries (API calls, subprocess).
Internal validation logic and helpers use real implementations.
"""

from argparse import Namespace
from unittest.mock import Mock, patch

from epycloud.commands import run


class TestRunWorkflowCommand:
    """Test run workflow command integration."""

    @patch("epycloud.lib.command_helpers.subprocess.run")
    @patch("epycloud.commands.run.cloud.workflow.requests.post")
    def test_run_workflow_cloud_success(self, mock_post, mock_subprocess, mock_config):
        """Test successful workflow submission to cloud."""
        # Mock only external boundaries
        mock_subprocess.return_value = Mock(returncode=0, stdout="mock-access-token\n", stderr="")

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
                    "workflows/epymodelingsuite-pipeline/executions/abc123",
            "state": "ACTIVE"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Use Namespace with real values, not Mock
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                task_count_per_node=None,
                stage_a_machine_type=None,
                stage_b_machine_type=None,
                stage_c_machine_type=None,
                forecast_repo_ref=None,
                output_config=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Validate
        assert exit_code == 0
        assert mock_post.called
        assert mock_subprocess.called

    def test_run_workflow_missing_config(self):
        """Test error handling when config is missing."""
        ctx = {
            "config": None,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(run_subcommand="workflow", exp_id="test"),
        }

        exit_code = run.handle(ctx)

        assert exit_code == 2  # Config error

    def test_run_workflow_invalid_exp_id(self, mock_config):
        """Test validation error for invalid exp_id."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="workflow",
                exp_id="../invalid",  # Path traversal
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                task_count_per_node=None,
                stage_a_machine_type=None,
                stage_b_machine_type=None,
                stage_c_machine_type=None,
                forecast_repo_ref=None,
                output_config=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        assert exit_code == 1  # Validation error

    def test_run_workflow_invalid_run_id(self, mock_config):
        """Test validation error for invalid run_id."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id="2025-11-07",  # Wrong format
                local=False,
                skip_output=False,
                max_parallelism=None,
                task_count_per_node=None,
                stage_a_machine_type=None,
                stage_b_machine_type=None,
                stage_c_machine_type=None,
                forecast_repo_ref=None,
                output_config=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        assert exit_code == 1  # Validation error

    @patch("epycloud.lib.command_helpers.subprocess.run")
    @patch("epycloud.commands.run.cloud.workflow.requests.post")
    def test_run_workflow_dry_run(self, mock_post, mock_subprocess, mock_config):
        """Test dry run mode doesn't make actual API calls."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="mock-token\n", stderr="")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": True,  # Dry run mode
            "args": Namespace(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                task_count_per_node=None,
                stage_a_machine_type=None,
                stage_b_machine_type=None,
                stage_c_machine_type=None,
                forecast_repo_ref=None,
                output_config=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should succeed without making actual API call
        assert exit_code == 0
        # requests.post should not be called in dry run
        assert not mock_post.called


class TestRunJobCommand:
    """Test run job command integration."""

    def test_run_job_stage_a_local(self, mock_config):
        """Test running stage A locally."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": True,  # Dry run to avoid actual docker execution
            "args": Namespace(
                run_subcommand="job",
                stage="A",
                exp_id="test-sim",
                run_id=None,
                task_index=0,
                num_tasks=None,
                output_config=None,
                local=True,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should succeed (dry run)
        assert exit_code == 0

    def test_run_job_stage_b_missing_run_id(self, mock_config):
        """Test stage B requires run_id."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="B",
                exp_id="test-sim",
                run_id=None,  # Missing run_id for stage B
                task_index=0,
                num_tasks=None,
                output_config=None,
                local=True,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should fail due to missing run_id
        assert exit_code == 1

    def test_run_job_stage_c_missing_num_tasks(self, mock_config):
        """Test stage C requires num_tasks."""
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
                num_tasks=None,  # Missing num_tasks for stage C
                output_config=None,
                local=True,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should fail due to missing num_tasks
        assert exit_code == 1

    def test_run_job_invalid_exp_id(self, mock_config):
        """Test job command with invalid exp_id."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="A",
                exp_id="test/invalid",  # Invalid character (slashes allowed, but not trailing/leading)
                run_id=None,
                task_index=0,
                num_tasks=None,
                output_config=None,
                local=True,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should fail due to validation error
        assert exit_code == 1


class TestRunWorkflowMachineTypeOverride:
    """Test machine type override integration in run workflow command."""

    @patch("epycloud.lib.validation.subprocess.run")
    @patch("epycloud.lib.command_helpers.subprocess.run")
    @patch("epycloud.commands.run.cloud.workflow.requests.post")
    def test_workflow_with_valid_machine_type_override(
        self, mock_post, mock_workflow_subprocess, mock_validation_subprocess, mock_config
    ):
        """Test workflow submission with valid machine type override."""
        # Mock gcloud commands for both validation and workflow
        mock_result = Mock(returncode=0, stdout="mock-token\n", stderr="")
        mock_validation_subprocess.return_value = mock_result
        mock_workflow_subprocess.return_value = mock_result

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/abc123"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Mock gcloud compute machine-types commands
        def subprocess_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get('args', [])
            cmd_str = ' '.join(cmd)

            if 'machine-types describe' in cmd_str:
                # Return machine type specs in JSON format
                import json
                return Mock(
                    returncode=0,
                    stdout=json.dumps({
                        "guestCpus": 8,
                        "memoryMb": 32768,
                        "name": "c2-standard-8"
                    }),
                    stderr=""
                )
            elif 'machine-types list' in cmd_str:
                # Return machine type list output (format=value(name) returns just names)
                return Mock(
                    returncode=0,
                    stdout='c2-standard-8\nn2-standard-4\nn2-standard-8\n',
                    stderr=""
                )
            # Default: return token
            return Mock(returncode=0, stdout="mock-token\n", stderr="")

        mock_validation_subprocess.side_effect = subprocess_side_effect
        mock_workflow_subprocess.side_effect = subprocess_side_effect

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                task_count_per_node=None,
                stage_a_machine_type=None,
                stage_b_machine_type="c2-standard-8",  # Override provided
                stage_c_machine_type=None,
                forecast_repo_ref=None,
                output_config=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should succeed
        assert exit_code == 0
        # API call should include the override
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        workflow_arg = call_kwargs["json"]["argument"]
        import json

        parsed_arg = json.loads(workflow_arg)
        assert "stageBMachineType" in parsed_arg
        assert parsed_arg["stageBMachineType"] == "c2-standard-8"

    @patch("epycloud.lib.validation.subprocess.run")
    def test_workflow_with_invalid_machine_type_rejects(self, mock_subprocess, mock_config):
        """Test workflow submission rejected with invalid machine type."""
        # Mock gcloud to return empty list (machine type not found)
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout='',  # Empty output = machine type not found
            stderr=""
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                task_count_per_node=None,
                stage_a_machine_type=None,
                stage_b_machine_type="invalid-type",  # Invalid override
                stage_c_machine_type=None,
                forecast_repo_ref=None,
                output_config=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should fail with validation error
        assert exit_code == 1

    @patch("epycloud.lib.command_helpers.subprocess.run")
    @patch("epycloud.commands.run.cloud.workflow.requests.post")
    def test_workflow_without_override_uses_default(
        self, mock_post, mock_subprocess, mock_config
    ):
        """Test workflow without override doesn't include stageBMachineType."""
        # Mock gcloud token fetch
        mock_subprocess.return_value = Mock(returncode=0, stdout="mock-token\n", stderr="")

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/abc123"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                task_count_per_node=None,
                stage_a_machine_type=None,
                stage_b_machine_type=None,  # No override
                stage_c_machine_type=None,
                forecast_repo_ref=None,
                output_config=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        # Should succeed
        assert exit_code == 0
        # API call should NOT include stageBMachineType
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        workflow_arg = call_kwargs["json"]["argument"]
        import json

        parsed_arg = json.loads(workflow_arg)
        assert "stageBMachineType" not in parsed_arg


class TestRunIdGeneration:
    """Test run ID generation."""

    def test_generate_run_id_format(self):
        """Test generated run ID has correct format."""
        from epycloud.lib.command_helpers import generate_run_id

        run_id = generate_run_id()

        # Should match format: YYYYMMDD-HHMMSS-xxxxxxxx
        import re

        pattern = r"^\d{8}-\d{6}-[a-f0-9]{8}$"
        assert re.match(pattern, run_id), f"Generated run_id {run_id} doesn't match expected format"

    def test_generate_run_id_uniqueness(self):
        """Test generated run IDs are unique."""
        from epycloud.lib.command_helpers import generate_run_id

        run_id_1 = generate_run_id()
        run_id_2 = generate_run_id()

        # Should be different (UUID part ensures uniqueness)
        assert run_id_1 != run_id_2
