"""Integration tests for run command."""

from unittest.mock import Mock, patch

from epycloud.commands import run


class TestRunWorkflowCommand:
    """Test run workflow command integration."""

    @patch("epycloud.commands.run.subprocess.run")
    @patch("epycloud.commands.run.requests.post")
    def test_run_workflow_cloud_success(self, mock_post, mock_subprocess, mock_config):
        """Test successful workflow submission to cloud."""
        # Setup mocks
        mock_subprocess.return_value = Mock(returncode=0, stdout="mock-access-token\n", stderr="")

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
                    "workflows/epymodelingsuite-pipeline/executions/abc123",
            "state": "ACTIVE"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Create context
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                stage_b_machine_type=None,
                wait=False,
                yes=True,
            ),
        }

        # Execute
        exit_code = run.handle(ctx)

        # Validate
        assert exit_code == 0
        assert mock_post.called
        assert mock_subprocess.called

        # Verify API call was made
        call_args = mock_post.call_args
        assert call_args is not None

    def test_run_workflow_missing_config(self):
        """Test error handling when config is missing."""
        ctx = {
            "config": None,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Mock(run_subcommand="workflow", exp_id="test"),
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
            "args": Mock(
                run_subcommand="workflow",
                exp_id="../invalid",  # Path traversal
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                stage_b_machine_type=None,
                wait=False,
                yes=True,
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
            "args": Mock(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id="2025-11-07",  # Wrong format
                local=False,
                skip_output=False,
                max_parallelism=None,
                stage_b_machine_type=None,
                wait=False,
                yes=True,
            ),
        }

        exit_code = run.handle(ctx)

        assert exit_code == 1  # Validation error

    def test_run_workflow_dry_run(self, mock_config):
        """Test dry run mode doesn't make actual API calls."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": True,  # Dry run mode
            "args": Mock(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                stage_b_machine_type=None,
                wait=False,
                yes=True,
            ),
        }

        with patch("epycloud.commands.run.subprocess.run") as mock_subprocess:
            with patch("epycloud.commands.run.requests.post") as mock_post:
                # Setup subprocess mock for token
                mock_subprocess.return_value = Mock(returncode=0, stdout="mock-token\n", stderr="")

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
            "args": Mock(
                run_subcommand="job",
                stage="A",
                exp_id="test-sim",
                run_id=None,
                task_index=0,
                num_tasks=None,
                local=True,
                wait=False,
                yes=True,
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
            "args": Mock(
                run_subcommand="job",
                stage="B",
                exp_id="test-sim",
                run_id=None,  # Missing run_id for stage B
                task_index=0,
                num_tasks=None,
                local=True,
                wait=False,
                yes=True,
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
            "args": Mock(
                run_subcommand="job",
                stage="C",
                exp_id="test-sim",
                run_id="20251107-100000-abc12345",
                task_index=0,
                num_tasks=None,  # Missing num_tasks for stage C
                local=True,
                wait=False,
                yes=True,
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
            "args": Mock(
                run_subcommand="job",
                stage="A",
                exp_id="test/invalid",  # Invalid character
                run_id=None,
                task_index=0,
                num_tasks=None,
                local=True,
                wait=False,
                yes=True,
            ),
        }

        exit_code = run.handle(ctx)

        # Should fail due to validation error
        assert exit_code == 1


class TestRunWorkflowMachineTypeOverride:
    """Test machine type override integration in run workflow command."""

    @patch("epycloud.commands.run.validate_machine_type")
    @patch("epycloud.commands.run.subprocess.run")
    @patch("epycloud.commands.run.requests.post")
    def test_workflow_with_valid_machine_type_override(
        self, mock_post, mock_subprocess, mock_validate, mock_config
    ):
        """Test workflow submission with valid machine type override."""
        # Mock validation to pass
        mock_validate.return_value = "c2-standard-8"

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
            "args": Mock(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                stage_b_machine_type="c2-standard-8",  # Override provided
                wait=False,
                yes=True,
            ),
        }

        exit_code = run.handle(ctx)

        # Should succeed
        assert exit_code == 0
        # Validation should be called with the override
        mock_validate.assert_called_once_with(
            "c2-standard-8", "test-project", "us-central1"
        )
        # API call should include the override
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        workflow_arg = call_kwargs["json"]["argument"]
        import json

        parsed_arg = json.loads(workflow_arg)
        assert "stageBMachineType" in parsed_arg
        assert parsed_arg["stageBMachineType"] == "c2-standard-8"

    @patch("epycloud.commands.run.validate_machine_type")
    def test_workflow_with_invalid_machine_type_rejects(self, mock_validate, mock_config):
        """Test workflow submission rejected with invalid machine type."""
        from epycloud.exceptions import ValidationError

        # Mock validation to fail
        mock_validate.side_effect = ValidationError(
            "Machine type 'invalid-type' not found in region us-central1"
        )

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                stage_b_machine_type="invalid-type",  # Invalid override
                wait=False,
                yes=True,
            ),
        }

        exit_code = run.handle(ctx)

        # Should fail with validation error
        assert exit_code == 1
        mock_validate.assert_called_once()

    @patch("epycloud.commands.run.subprocess.run")
    @patch("epycloud.commands.run.requests.post")
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
            "args": Mock(
                run_subcommand="workflow",
                exp_id="test-sim",
                run_id=None,
                local=False,
                skip_output=False,
                max_parallelism=None,
                stage_b_machine_type=None,  # No override
                wait=False,
                yes=True,
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
