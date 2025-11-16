"""Integration tests for terraform command."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from epycloud.commands import terraform


class TestTerraformInitCommand:
    """Test terraform init command."""

    @patch("epycloud.commands.terraform.subprocess.run")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_init_success(
        self, mock_require_config, mock_root, mock_subprocess, mock_config, tmp_path
    ):
        """Test successful terraform initialization."""
        # Setup terraform directory
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_subprocess.return_value = Mock(returncode=0)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(terraform_subcommand="init"),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == ["terraform", "init"]
        assert call_args[1]["cwd"] == terraform_dir

    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_init_directory_not_found(
        self, mock_require_config, mock_root, mock_config, tmp_path
    ):
        """Test error when terraform directory doesn't exist."""
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        # Don't create terraform directory

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(terraform_subcommand="init"),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_init_dry_run(
        self, mock_require_config, mock_root, mock_config, tmp_path
    ):
        """Test terraform init dry run mode."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(terraform_subcommand="init"),
        }

        with patch("epycloud.commands.terraform.subprocess.run") as mock_subprocess:
            exit_code = terraform.handle(ctx)

            # Dry run should not call subprocess
            assert exit_code == 0

    @patch("epycloud.commands.terraform.subprocess.run")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_init_command_not_found(
        self, mock_require_config, mock_root, mock_subprocess, mock_config, tmp_path
    ):
        """Test error when terraform command is not found."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_subprocess.side_effect = FileNotFoundError()

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(terraform_subcommand="init"),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.terraform.subprocess.run")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_init_failure(
        self, mock_require_config, mock_root, mock_subprocess, mock_config, tmp_path
    ):
        """Test terraform init failure."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_subprocess.return_value = Mock(returncode=1)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(terraform_subcommand="init"),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 1


class TestTerraformPlanCommand:
    """Test terraform plan command."""

    @patch("epycloud.commands.terraform.subprocess.run")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_plan_success(
        self, mock_require_config, mock_root, mock_subprocess, mock_config, tmp_path
    ):
        """Test successful terraform plan."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_subprocess.return_value = Mock(returncode=0)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(terraform_subcommand="plan", target=None),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0
        call_args = mock_subprocess.call_args[0][0]
        assert call_args == ["terraform", "plan"]

    @patch("epycloud.commands.terraform.subprocess.run")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_plan_with_target(
        self, mock_require_config, mock_root, mock_subprocess, mock_config, tmp_path
    ):
        """Test terraform plan with target resource."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_subprocess.return_value = Mock(returncode=0)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                terraform_subcommand="plan",
                target="google_storage_bucket.data_bucket",
            ),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0
        call_args = mock_subprocess.call_args[0][0]
        assert "-target" in call_args
        assert "google_storage_bucket.data_bucket" in call_args

    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_plan_dry_run(
        self, mock_require_config, mock_root, mock_config, tmp_path
    ):
        """Test terraform plan dry run mode."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(terraform_subcommand="plan", target=None),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0


class TestTerraformApplyCommand:
    """Test terraform apply command."""

    @patch("epycloud.commands.terraform.subprocess.run")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_apply_with_auto_approve(
        self, mock_require_config, mock_root, mock_subprocess, mock_config, tmp_path
    ):
        """Test terraform apply with auto-approve flag."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_subprocess.return_value = Mock(returncode=0)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                terraform_subcommand="apply",
                auto_approve=True,
                target=None,
            ),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0
        call_args = mock_subprocess.call_args[0][0]
        assert "-auto-approve" in call_args

    @patch("epycloud.commands.terraform.ask_confirmation")
    @patch("epycloud.commands.terraform.subprocess.run")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_apply_prod_requires_confirmation(
        self,
        mock_require_config,
        mock_root,
        mock_subprocess,
        mock_confirm,
        mock_config,
        tmp_path,
    ):
        """Test terraform apply in production requires confirmation."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_subprocess.return_value = Mock(returncode=0)
        mock_confirm.return_value = True

        ctx = {
            "config": mock_config,
            "environment": "prod",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                terraform_subcommand="apply",
                auto_approve=False,
                target=None,
            ),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0
        mock_confirm.assert_called_once()

    @patch("epycloud.commands.terraform.ask_confirmation")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_apply_prod_cancelled(
        self, mock_require_config, mock_root, mock_confirm, mock_config, tmp_path
    ):
        """Test terraform apply cancelled in production."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_confirm.return_value = False

        ctx = {
            "config": mock_config,
            "environment": "prod",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                terraform_subcommand="apply",
                auto_approve=False,
                target=None,
            ),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0
        mock_confirm.assert_called_once()

    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_apply_dry_run(
        self, mock_require_config, mock_root, mock_config, tmp_path
    ):
        """Test terraform apply dry run mode."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(
                terraform_subcommand="apply",
                auto_approve=False,
                target=None,
            ),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0


class TestTerraformDestroyCommand:
    """Test terraform destroy command."""

    @patch("epycloud.commands.terraform.ask_confirmation")
    @patch("epycloud.commands.terraform.subprocess.run")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_destroy_with_confirmation(
        self,
        mock_require_config,
        mock_root,
        mock_subprocess,
        mock_confirm,
        mock_config,
        tmp_path,
    ):
        """Test terraform destroy with confirmation."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_subprocess.return_value = Mock(returncode=0)
        mock_confirm.return_value = True

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                terraform_subcommand="destroy",
                auto_approve=False,
                target=None,
            ),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0
        mock_confirm.assert_called_once()

    @patch("epycloud.commands.terraform.subprocess.run")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_destroy_with_auto_approve(
        self, mock_require_config, mock_root, mock_subprocess, mock_config, tmp_path
    ):
        """Test terraform destroy with auto-approve flag."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_subprocess.return_value = Mock(returncode=0)

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                terraform_subcommand="destroy",
                auto_approve=True,
                target=None,
            ),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0
        call_args = mock_subprocess.call_args[0][0]
        assert "-auto-approve" in call_args

    @patch("epycloud.commands.terraform.ask_confirmation")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_destroy_cancelled(
        self, mock_require_config, mock_root, mock_confirm, mock_config, tmp_path
    ):
        """Test terraform destroy cancelled by user."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_confirm.return_value = False

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                terraform_subcommand="destroy",
                auto_approve=False,
                target=None,
            ),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0
        mock_confirm.assert_called_once()

    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_destroy_dry_run(
        self, mock_require_config, mock_root, mock_config, tmp_path
    ):
        """Test terraform destroy dry run mode."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(
                terraform_subcommand="destroy",
                auto_approve=False,
                target=None,
            ),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0


class TestTerraformOutputCommand:
    """Test terraform output command."""

    @patch("epycloud.commands.terraform.subprocess.run")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_output_success(
        self, mock_require_config, mock_root, mock_subprocess, mock_config, tmp_path
    ):
        """Test successful terraform output."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_subprocess.return_value = Mock(returncode=0)

        args = Mock(terraform_subcommand="output")
        args.name = None

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.terraform.subprocess.run")
    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_output_specific_name(
        self, mock_require_config, mock_root, mock_subprocess, mock_config, tmp_path
    ):
        """Test terraform output with specific output name."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config
        mock_subprocess.return_value = Mock(returncode=0)

        args = Mock(terraform_subcommand="output")
        args.name = "bucket_name"

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0
        call_args = mock_subprocess.call_args[0][0]
        assert "bucket_name" in call_args

    @patch("epycloud.commands.terraform.get_project_root")
    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_output_dry_run(
        self, mock_require_config, mock_root, mock_config, tmp_path
    ):
        """Test terraform output dry run mode."""
        terraform_dir = tmp_path / "terraform"
        terraform_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_require_config.return_value = mock_config

        args = Mock(terraform_subcommand="output")
        args.name = None

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": args,
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 0


class TestTerraformEnvVars:
    """Test terraform environment variables construction."""

    def test_get_terraform_env_vars_basic(self, mock_config):
        """Test constructing basic TF_VAR environment variables."""
        env_vars = terraform._get_terraform_env_vars(mock_config)

        assert env_vars["TF_VAR_project_id"] == "test-project"
        assert env_vars["TF_VAR_region"] == "us-central1"
        assert env_vars["TF_VAR_bucket_name"] == "test-bucket"
        assert env_vars["TF_VAR_repo_name"] == "epymodelingsuite-repo"
        assert env_vars["TF_VAR_image_name"] == "epymodelingsuite"
        assert env_vars["TF_VAR_image_tag"] == "latest"

    def test_get_terraform_env_vars_with_batch_config(self):
        """Test constructing TF_VAR environment variables with batch config."""
        config = {
            "google_cloud": {
                "project_id": "test-project",
                "region": "us-central1",
                "bucket_name": "test-bucket",
                "batch": {
                    "task_count_per_node": 1,
                    "stage_a": {
                        "cpu_milli": 2000,
                        "memory_mib": 4096,
                        "machine_type": "e2-standard-2",
                        "max_run_duration": 3600,
                    },
                    "stage_b": {
                        "cpu_milli": 4000,
                        "memory_mib": 8192,
                        "machine_type": "n2-standard-4",
                        "max_run_duration": 36000,
                    },
                    "stage_c": {
                        "cpu_milli": 2000,
                        "memory_mib": 8192,
                        "run_output_stage": True,
                        "max_run_duration": 7200,
                    },
                },
            },
            "docker": {
                "repo_name": "test-repo",
                "image_name": "test-image",
                "image_tag": "latest",
            },
            "github": {
                "forecast_repo": "mobs-lab/flu-forecast",
            },
        }

        env_vars = terraform._get_terraform_env_vars(config)

        # Check batch config
        assert env_vars["TF_VAR_task_count_per_node"] == "1"

        # Check stage A
        assert env_vars["TF_VAR_stage_a_cpu_milli"] == "2000"
        assert env_vars["TF_VAR_stage_a_memory_mib"] == "4096"
        assert env_vars["TF_VAR_stage_a_machine_type"] == "e2-standard-2"
        assert env_vars["TF_VAR_stage_a_max_run_duration"] == "3600"

        # Check stage B
        assert env_vars["TF_VAR_stage_b_cpu_milli"] == "4000"
        assert env_vars["TF_VAR_stage_b_memory_mib"] == "8192"
        assert env_vars["TF_VAR_stage_b_machine_type"] == "n2-standard-4"
        assert env_vars["TF_VAR_stage_b_max_run_duration"] == "36000"

        # Check stage C
        assert env_vars["TF_VAR_stage_c_cpu_milli"] == "2000"
        assert env_vars["TF_VAR_stage_c_memory_mib"] == "8192"
        assert env_vars["TF_VAR_run_output_stage"] == "true"
        assert env_vars["TF_VAR_stage_c_max_run_duration"] == "7200"

        # Check GitHub
        assert env_vars["TF_VAR_github_forecast_repo"] == "mobs-lab/flu-forecast"

    def test_get_terraform_env_vars_partial_config(self):
        """Test constructing TF_VAR environment variables with partial config."""
        config = {
            "google_cloud": {
                "project_id": "test-project",
                # Missing region and bucket_name
            },
            "docker": {},
            "github": {},
        }

        env_vars = terraform._get_terraform_env_vars(config)

        assert env_vars["TF_VAR_project_id"] == "test-project"
        assert "TF_VAR_region" not in env_vars
        assert "TF_VAR_bucket_name" not in env_vars


class TestTerraformNoSubcommand:
    """Test terraform command without subcommand."""

    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_no_subcommand_prints_help(self, mock_require_config, mock_config):
        """Test that no subcommand prints help."""
        mock_require_config.return_value = mock_config
        mock_parser = Mock()

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(terraform_subcommand=None, _terraform_parser=mock_parser),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 1
        mock_parser.print_help.assert_called_once()

    @patch("epycloud.commands.terraform.require_config")
    def test_terraform_unknown_subcommand(self, mock_require_config, mock_config):
        """Test error for unknown subcommand."""
        mock_require_config.return_value = mock_config

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(terraform_subcommand="unknown"),
        }

        exit_code = terraform.handle(ctx)

        assert exit_code == 1

    def test_terraform_missing_config(self):
        """Test error when config is missing."""
        from epycloud.exceptions import ConfigError

        with patch("epycloud.commands.terraform.require_config") as mock_require:
            mock_require.side_effect = ConfigError("Config not found")

            ctx = {
                "config": None,
                "environment": "dev",
                "profile": None,
                "verbose": False,
                "quiet": False,
                "dry_run": False,
                "args": Mock(terraform_subcommand="init"),
            }

            exit_code = terraform.handle(ctx)

            assert exit_code == 2
