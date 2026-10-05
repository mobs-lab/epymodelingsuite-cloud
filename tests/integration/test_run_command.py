"""Integration tests for run command.

Tests use minimal mocking - only external boundaries (API calls, subprocess).
Internal validation logic and helpers use real implementations.
"""

from argparse import Namespace
from unittest.mock import Mock, patch

import pytest

from epycloud.cli import _is_dry_run, create_parser
from epycloud.commands import run
from epycloud.exceptions import ValidationError
from epycloud.execution.gcp_machines import MACHINE_SPECS


@pytest.fixture(autouse=True)
def machine_metadata_without_gcloud(monkeypatch):
    """Keep command tests at the submission boundary while candidate tests cover lookup I/O."""
    from epycloud.commands.run import validation

    def validate(machine_type, project_id, region):
        del project_id, region
        if machine_type.startswith("invalid"):
            raise ValidationError(f"Machine type '{machine_type}' not found")
        return machine_type

    def specs(machine_type, project_id, region):
        del project_id, region
        vcpus, memory_mib = MACHINE_SPECS[machine_type]
        return vcpus * 1000, memory_mib

    monkeypatch.setattr(validation, "validate_machine_type", validate)
    monkeypatch.setattr(validation, "get_machine_type_specs", specs)


class TestRunWorkflowCommand:
    """Test run workflow command integration."""

    @patch("epycloud.lib.command_helpers.subprocess.run")
    @patch("epycloud.commands.run.cloud.workflow.requests.post")
    def test_run_workflow_cloud_success(self, mock_post, mock_subprocess, mock_config):
        """A normal workflow submission forwards resolved chains and their legacy heads."""
        for stage in ("stage_a", "stage_b", "stage_c"):
            stage_config = mock_config["google_cloud"]["batch"][stage]
            stage_config["machine_types"] = [stage_config.pop("machine_type")]
        mock_config["google_cloud"]["batch"]["stage_b"]["machine_types"].append("c4-standard-4")
        # Mock only external boundaries
        mock_subprocess.return_value = Mock(returncode=0, stdout="mock-access-token\n", stderr="")

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/abc123",
            "state": "ACTIVE",
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

        # Confirm all 9 stage resource keys were forwarded with the fixture's
        # google_cloud.batch.stage_* values (regression guard for the bug where
        # config-resolved stage resources were dropped from the workflow input).
        import json

        parsed_arg = json.loads(mock_post.call_args[1]["json"]["argument"])
        assert parsed_arg["stageAMachineType"] == "c4d-standard-2"
        assert parsed_arg["stageACpuMilli"] == 2000
        assert parsed_arg["stageAMemoryMib"] == 7168
        assert parsed_arg["stageBMachineType"] == "c4d-standard-4"
        assert parsed_arg["stageBCpuMilli"] == 4000
        assert parsed_arg["stageBMemoryMib"] == 15360
        assert parsed_arg["stageCMachineType"] == "c4d-standard-8"
        assert parsed_arg["stageCCpuMilli"] == 8000
        assert parsed_arg["stageCMemoryMib"] == 31744
        assert parsed_arg["stageBCandidates"] == [
            {
                "machine_type": "c4d-standard-4",
                "cpu_milli": 4000,
                "memory_mib": 15360,
                "task_count_per_node": 1,
            },
            {
                "machine_type": "c4-standard-4",
                "cpu_milli": 4000,
                "memory_mib": 15360,
                "task_count_per_node": 1,
            },
        ]
        assert parsed_arg["stageBPinned"] is False

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

    @pytest.mark.parametrize(
        "arguments",
        [
            ["--dry-run", "run", "workflow", "--exp-id", "test-sim"],
            ["run", "workflow", "--exp-id", "test-sim", "--dry-run"],
        ],
    )
    def test_dry_run_is_honored_before_or_after_the_subcommand(self, arguments):
        """A command-level default must never shadow a global no-write request."""
        args = create_parser().parse_args(arguments)

        assert _is_dry_run(args) is True

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
        # Read-only Terraform discovery is allowed, but auth/submission is not.
        commands = [" ".join(call.args[0]) for call in mock_subprocess.call_args_list]
        assert all("gcloud auth print-access-token" not in command for command in commands)


class TestRunJobCommand:
    """Test run job command integration."""

    def test_run_job_parser_accepts_fresh(self):
        """The repair command parser records ``--fresh`` as an enabled flag."""
        args = create_parser().parse_args(
            [
                "run",
                "job",
                "--stage",
                "B",
                "--exp-id",
                "test-sim",
                "--run-id",
                "test-run",
                "--fresh",
            ]
        )

        assert args.fresh is True

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

    @patch("epycloud.commands.run.local.job.run_docker_compose_stage", return_value=0)
    def test_run_job_stage_b_reuses_completed_results_by_default(self, mock_compose, mock_config):
        """Naming a prior Stage B run enables completed-result reuse by default."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="B",
                exp_id="test-sim",
                run_id="test-run",
                task_index=3,
                num_tasks=None,
                output_config=None,
                local=True,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        assert run.handle(ctx) == 0
        assert mock_compose.call_args.kwargs["env_vars"]["SKIP_EXISTING"] == "true"

    @patch("epycloud.commands.run.local.job.run_docker_compose_stage", return_value=0)
    def test_run_job_stage_b_fresh_disables_result_reuse(self, mock_compose, mock_config):
        """The ``--fresh`` repair path disables completed-result reuse."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "verbose": False,
            "dry_run": False,
            "args": Namespace(
                run_subcommand="job",
                stage="B",
                exp_id="test-sim",
                run_id="test-run",
                task_index=3,
                num_tasks=None,
                output_config=None,
                local=True,
                fresh=True,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        assert run.handle(ctx) == 0
        assert mock_compose.call_args.kwargs["env_vars"]["SKIP_EXISTING"] == "false"

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
                exp_id="test/invalid",  # Slashes allowed but not trailing/leading
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


class TestCloudProviderDispatch:
    """Provider selection occurs before provider-specific command preparation."""

    @patch("epycloud.commands.run.handlers.run_job_gcp")
    @patch("epycloud.commands.run.handlers.get_execution_backend")
    def test_job_does_not_enter_gcp_adapter_for_another_backend(
        self, mock_get_backend, mock_run_gcp
    ):
        mock_get_backend.return_value = Mock(provider="aws")
        ctx = {
            "config": {"execution": {"provider": "aws"}},
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

        assert run.handle(ctx) == 2
        mock_run_gcp.assert_not_called()

    @patch("epycloud.commands.run.handlers.run_workflow_gcp")
    @patch("epycloud.commands.run.handlers.get_execution_backend")
    def test_workflow_does_not_enter_gcp_adapter_for_another_backend(
        self, mock_get_backend, mock_run_gcp
    ):
        mock_get_backend.return_value = Mock(provider="aws")
        ctx = {
            "config": {"execution": {"provider": "aws"}},
            "environment": "dev",
            "profile": None,
            "verbose": False,
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

        assert run.handle(ctx) == 2
        mock_run_gcp.assert_not_called()


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
            cmd = args[0] if args else kwargs.get("args", [])
            cmd_str = " ".join(cmd)

            if "machine-types describe" in cmd_str:
                # Return machine type specs in JSON format
                import json

                return Mock(
                    returncode=0,
                    stdout=json.dumps({"guestCpus": 8, "memoryMb": 32768, "name": "c4-standard-8"}),
                    stderr="",
                )
            elif "machine-types list" in cmd_str:
                # Return machine type list output (format=value(name) returns just names)
                return Mock(
                    returncode=0, stdout="c4-standard-8\nn2-standard-4\nn2-standard-8\n", stderr=""
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
                stage_b_machine_type="c4-standard-8",  # Override provided
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
        # CLI override takes precedence over the fixture's profile value
        # (mock_config sets stage_b.machine_type = "c4d-standard-4").
        assert parsed_arg["stageBMachineType"] == "c4-standard-8"
        # A pinned machine keeps the configured per-task request (4000 mCPU, 15360 MiB);
        # (30720 - 1024) // 15360 leaves room for one task.
        assert parsed_arg["stageBCandidates"] == [
            {
                "machine_type": "c4-standard-8",
                "cpu_milli": 4000,
                "memory_mib": 15360,
                "task_count_per_node": 1,
            },
        ]
        assert parsed_arg["stageBPinned"] is True

    @patch("epycloud.lib.validation.subprocess.run")
    def test_workflow_with_invalid_machine_type_rejects(self, mock_subprocess, mock_config):
        """Test workflow submission rejected with invalid machine type."""
        # Mock gcloud to return empty list (machine type not found)
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="",  # Empty output = machine type not found
            stderr="",
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
    def test_workflow_forwards_profile_stage_resources_without_cli_override(
        self, mock_post, mock_subprocess, mock_config
    ):
        """Stage resources from config (no CLI override) reach the workflow input.

        Regression test for the bug where ``epycloud run workflow`` only forwarded
        stage machine types when ``--stage-*-machine-type`` was passed on the CLI,
        causing profile-set resources (e.g. flu's ``c4d-standard-8`` for Stage C)
        to be silently replaced with the workflow YAML's terraform defaults.
        """
        mock_subprocess.return_value = Mock(returncode=0, stdout="mock-token\n", stderr="")

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
                stage_b_machine_type=None,  # No CLI override
                stage_c_machine_type=None,
                forecast_repo_ref=None,
                output_config=None,
                wait=False,
                yes=True,
                project_directory=None,
            ),
        }

        exit_code = run.handle(ctx)

        assert exit_code == 0
        assert mock_post.called
        import json

        parsed_arg = json.loads(mock_post.call_args[1]["json"]["argument"])
        # All three stages should now appear with the fixture's profile values.
        assert parsed_arg["stageAMachineType"] == "c4d-standard-2"
        assert parsed_arg["stageBMachineType"] == "c4d-standard-4"
        assert parsed_arg["stageCMachineType"] == "c4d-standard-8"
        assert parsed_arg["stageACpuMilli"] == 2000
        assert parsed_arg["stageBCpuMilli"] == 4000
        assert parsed_arg["stageCCpuMilli"] == 8000
        assert parsed_arg["stageAMemoryMib"] == 7168
        assert parsed_arg["stageBMemoryMib"] == 15360
        assert parsed_arg["stageCMemoryMib"] == 31744

    @patch("epycloud.lib.command_helpers.subprocess.run")
    @patch("epycloud.commands.run.cloud.workflow.requests.post")
    def test_workflow_omits_stage_keys_when_config_absent(
        self, mock_post, mock_subprocess, mock_config
    ):
        """When google_cloud.batch is unset, no stage keys are forwarded.

        Preserves the original "absent → omitted" guarantee so the workflow
        falls back to its terraform-baked defaults.
        """
        mock_subprocess.return_value = Mock(returncode=0, stdout="mock-token\n", stderr="")

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/abc123"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Strip the batch section so no stage_* machine_type can be resolved.
        mock_config["google_cloud"].pop("batch", None)

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

        assert exit_code == 0
        assert mock_post.called
        import json

        parsed_arg = json.loads(mock_post.call_args[1]["json"]["argument"])
        for key in (
            "stageAMachineType",
            "stageACpuMilli",
            "stageAMemoryMib",
            "stageBMachineType",
            "stageBCpuMilli",
            "stageBMemoryMib",
            "stageCMachineType",
            "stageCCpuMilli",
            "stageCMemoryMib",
        ):
            assert key not in parsed_arg


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


class TestWorkflowBillingLabels:
    """Test profile and billing_project labels flow through to workflow args."""

    @patch("epycloud.lib.command_helpers.subprocess.run")
    @patch("epycloud.commands.run.cloud.workflow.requests.post")
    def test_workflow_includes_profile_from_meta(self, mock_post, mock_subprocess, mock_config):
        """Test workflow args include profile from _meta."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="mock-token\n", stderr="")

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/abc123"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # mock_config already has _meta.profile.name = "test"
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

        assert exit_code == 0
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        import json

        parsed_arg = json.loads(call_kwargs["json"]["argument"])
        assert parsed_arg["profile"] == "test"

    @patch("epycloud.lib.command_helpers.subprocess.run")
    @patch("epycloud.commands.run.cloud.workflow.requests.post")
    def test_workflow_includes_billing_project(self, mock_post, mock_subprocess, mock_config):
        """Test workflow args include billing_project when configured."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="mock-token\n", stderr="")

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/abc123"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Set billing_project in config
        mock_config["google_cloud"]["billing_project"] = "flu-forecasting"

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

        assert exit_code == 0
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        import json

        parsed_arg = json.loads(call_kwargs["json"]["argument"])
        assert parsed_arg["billingProject"] == "flu-forecasting"

    @patch("epycloud.lib.command_helpers.subprocess.run")
    @patch("epycloud.commands.run.cloud.workflow.requests.post")
    def test_workflow_handles_none_profile_metadata(self, mock_post, mock_subprocess, mock_config):
        """Test workflow handles None profile metadata without crashing."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="mock-token\n", stderr="")

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/abc123"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Set profile metadata to None (no profile active)
        mock_config["_meta"]["profile"] = None

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

        assert exit_code == 0
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        import json

        parsed_arg = json.loads(call_kwargs["json"]["argument"])
        # Profile should be omitted when metadata is None
        assert "profile" not in parsed_arg

    @patch("epycloud.lib.command_helpers.subprocess.run")
    @patch("epycloud.commands.run.cloud.workflow.requests.post")
    def test_workflow_omits_empty_billing_project(self, mock_post, mock_subprocess, mock_config):
        """Test workflow args omit billingProject when empty."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="mock-token\n", stderr="")

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/us-central1/"
            "workflows/epymodelingsuite-pipeline/executions/abc123"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # billing_project is empty in mock_config by default
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

        assert exit_code == 0
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        import json

        parsed_arg = json.loads(call_kwargs["json"]["argument"])
        assert "billingProject" not in parsed_arg
