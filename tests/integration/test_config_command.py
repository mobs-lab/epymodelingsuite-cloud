"""Integration tests for config command."""

import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock

import pytest
import yaml

from epycloud.commands import config_cmd


class TestConfigInitCommand:
    """Test config init command."""

    @patch("epycloud.commands.config_cmd.operations.get_config_dir")
    @patch("epycloud.commands.config_cmd.operations.shutil.copy")
    @patch("epycloud.commands.config_cmd.operations.os.chmod")
    def test_config_init_creates_directory(
        self, mock_chmod, mock_copy, mock_config_dir, tmp_path
    ):
        """Test that init creates config directory and copies templates."""
        config_dir = tmp_path / ".config" / "epymodelingsuite-cloud"
        mock_config_dir.return_value = config_dir

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="init"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0
        # Verify directory structure created
        assert config_dir.exists()
        assert (config_dir / "environments").exists()
        assert (config_dir / "profiles").exists()
        # Verify templates were copied
        assert mock_copy.called
        # Verify permissions set on secrets file
        assert mock_chmod.called

    @patch("epycloud.commands.config_cmd.operations.get_config_dir")
    @patch("epycloud.commands.config_cmd.operations.shutil.copy")
    @patch("epycloud.commands.config_cmd.operations.os.chmod")
    def test_config_init_skips_existing_files(
        self, mock_chmod, mock_copy, mock_config_dir, tmp_path
    ):
        """Test that init skips existing files."""
        config_dir = tmp_path / ".config" / "epymodelingsuite-cloud"
        config_dir.mkdir(parents=True)
        (config_dir / "environments").mkdir()
        (config_dir / "profiles").mkdir()
        # Create existing config file
        (config_dir / "config.yaml").write_text("existing: true")
        mock_config_dir.return_value = config_dir

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="init"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0
        # config.yaml should not be copied since it exists
        # Only other templates should be copied

    @patch("epycloud.commands.config_cmd.operations.get_config_dir")
    @patch("epycloud.commands.config_cmd.operations.shutil.copy")
    @patch("epycloud.commands.config_cmd.operations.os.chmod")
    def test_config_init_sets_default_profile(
        self, mock_chmod, mock_copy, mock_config_dir, tmp_path
    ):
        """Test that init sets default profile to flu."""
        config_dir = tmp_path / ".config" / "epymodelingsuite-cloud"
        mock_config_dir.return_value = config_dir

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="init"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0
        active_profile_file = config_dir / "active_profile"
        assert active_profile_file.exists()
        assert active_profile_file.read_text().strip() == "flu"


class TestConfigShowCommand:
    """Test config show command."""

    @patch("epycloud.lib.command_helpers.require_config")
    def test_config_show_displays_config(self, mock_require_config, mock_config):
        """Test that show displays current configuration."""
        mock_require_config.return_value = mock_config

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": "flu",
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="show", raw=False),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.lib.command_helpers.require_config")
    @patch("epycloud.commands.config_cmd.handlers.yaml.dump")
    def test_config_show_raw_yaml(self, mock_dump, mock_require_config, mock_config):
        """Test that show --raw outputs raw YAML."""
        mock_require_config.return_value = mock_config

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="show", raw=True),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0
        assert mock_dump.called

    @patch("epycloud.lib.command_helpers.require_config")
    def test_config_show_with_metadata(self, mock_require_config, mock_config):
        """Test that show displays profile metadata."""
        config_with_meta = dict(mock_config)
        config_with_meta["_meta"] = {
            "profile": {
                "name": "flu",
                "description": "Flu modeling profile",
                "version": "1.0.0",
            },
            "config_sources": ["config.yaml", "dev.yaml", "flu.yaml"],
        }
        mock_require_config.return_value = config_with_meta

        ctx = {
            "config": config_with_meta,
            "environment": "dev",
            "profile": "flu",
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="show", raw=False),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.lib.command_helpers.require_config")
    def test_config_show_missing_config(self, mock_require_config):
        """Test error when config cannot be loaded."""
        from epycloud.exceptions import ConfigError

        mock_require_config.side_effect = ConfigError("Config not found")

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="show", raw=False),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 1


class TestConfigEditCommand:
    """Test config edit command."""

    @patch("epycloud.commands.config_cmd.operations.subprocess.run")
    @patch("epycloud.commands.config_cmd.operations.get_config_file")
    @patch.dict(os.environ, {"EDITOR": "vim"})
    def test_config_edit_opens_editor(self, mock_get_file, mock_subprocess):
        """Test that edit opens config file in editor."""
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_get_file.return_value = mock_file
        mock_subprocess.return_value = Mock(returncode=0)

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="edit", edit_env=None),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0] == "vim"

    @patch("epycloud.commands.config_cmd.operations.subprocess.run")
    @patch("epycloud.commands.config_cmd.operations.get_environment_file")
    @patch.dict(os.environ, {"EDITOR": "nano"})
    def test_config_edit_env_file(self, mock_get_env_file, mock_subprocess):
        """Test editing environment-specific config."""
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_get_env_file.return_value = mock_file
        mock_subprocess.return_value = Mock(returncode=0)

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="edit", edit_env="prod"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0
        mock_get_env_file.assert_called_once_with("prod")

    @patch("epycloud.commands.config_cmd.operations.get_config_file")
    def test_config_edit_file_not_found(self, mock_get_file):
        """Test error when config file doesn't exist."""
        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_get_file.return_value = mock_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="edit", edit_env=None),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.config_cmd.operations.subprocess.run")
    @patch("epycloud.commands.config_cmd.operations.get_config_file")
    @patch.dict(os.environ, {"EDITOR": "nonexistent-editor"})
    def test_config_edit_editor_not_found(self, mock_get_file, mock_subprocess):
        """Test error when editor is not found."""
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_get_file.return_value = mock_file
        mock_subprocess.side_effect = FileNotFoundError()

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="edit", edit_env=None),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.config_cmd.operations.subprocess.run")
    @patch("epycloud.commands.config_cmd.operations.get_config_file")
    @patch.dict(os.environ, {"EDITOR": "vim"})
    def test_config_edit_editor_fails(self, mock_get_file, mock_subprocess):
        """Test error when editor process fails."""
        import subprocess

        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_get_file.return_value = mock_file
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "vim")

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="edit", edit_env=None),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 1


class TestConfigEditSecretsCommand:
    """Test config edit-secrets command."""

    @patch("epycloud.commands.config_cmd.operations.subprocess.run")
    @patch("epycloud.commands.config_cmd.operations.os.chmod")
    @patch("epycloud.commands.config_cmd.operations.get_secrets_file")
    @patch.dict(os.environ, {"EDITOR": "vim"})
    def test_config_edit_secrets_opens_editor(
        self, mock_get_file, mock_chmod, mock_subprocess, tmp_path
    ):
        """Test that edit-secrets opens secrets file in editor."""
        secrets_file = tmp_path / "secrets.yaml"
        secrets_file.write_text("github:\n  personal_access_token: ''\n")
        # Set correct permissions so no chmod is needed
        os.chmod(secrets_file, 0o600)
        mock_get_file.return_value = secrets_file
        mock_subprocess.return_value = Mock(returncode=0)

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="edit-secrets"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0
        mock_subprocess.assert_called_once()

    @patch("epycloud.commands.config_cmd.operations.subprocess.run")
    @patch("epycloud.commands.config_cmd.operations.os.chmod")
    @patch("epycloud.commands.config_cmd.operations.get_secrets_file")
    @patch.dict(os.environ, {"EDITOR": "vim"})
    def test_config_edit_secrets_creates_file_if_missing(
        self, mock_get_file, mock_chmod, mock_subprocess, tmp_path
    ):
        """Test that edit-secrets creates file if it doesn't exist."""
        secrets_file = tmp_path / "secrets.yaml"
        mock_get_file.return_value = secrets_file
        mock_subprocess.return_value = Mock(returncode=0)

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="edit-secrets"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0
        assert secrets_file.exists()
        # Verify chmod was called to set permissions to 0600
        mock_chmod.assert_called()

    @patch("epycloud.commands.config_cmd.operations.subprocess.run")
    @patch("epycloud.commands.config_cmd.operations.os.chmod")
    @patch("epycloud.commands.config_cmd.operations.get_secrets_file")
    @patch.dict(os.environ, {"EDITOR": "vim"})
    def test_config_edit_secrets_fixes_permissions(
        self, mock_get_file, mock_chmod, mock_subprocess, tmp_path
    ):
        """Test that edit-secrets fixes insecure permissions."""
        secrets_file = tmp_path / "secrets.yaml"
        secrets_file.write_text("test")
        # Set insecure permissions
        os.chmod(secrets_file, 0o644)
        mock_get_file.return_value = secrets_file
        mock_subprocess.return_value = Mock(returncode=0)

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="edit-secrets"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0
        # Verify permissions were fixed
        mock_chmod.assert_called_with(secrets_file, 0o600)


class TestConfigValidateCommand:
    """Test config validate command."""

    @patch("epycloud.config.loader.ConfigLoader")
    @patch("epycloud.commands.config_cmd.handlers.get_config_value")
    def test_config_validate_success(self, mock_get_value, mock_loader):
        """Test successful validation."""
        mock_config = {
            "google_cloud": {
                "project_id": "my-project",
                "region": "us-central1",
                "bucket_name": "my-bucket",
            },
            "github": {"personal_access_token": "ghp_realtoken"},
        }
        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = mock_config
        mock_loader.return_value = mock_loader_instance

        def get_value_side_effect(config, key):
            parts = key.split(".")
            val = config
            for part in parts:
                val = val.get(part, None)
                if val is None:
                    return None
            return val

        mock_get_value.side_effect = get_value_side_effect

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="validate"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0

    def test_config_validate_missing_fields(self, tmp_path, monkeypatch):
        """Test validation fails for missing required fields."""
        # Create temp config directory
        config_dir = tmp_path / "epymodelingsuite-cloud"
        config_dir.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Write config with placeholder values
        config_file = config_dir / "config.yaml"
        config_file.write_text("""
google_cloud:
  project_id: your-project-id  # Placeholder value
  region: us-central1
  bucket_name: my-bucket
github:
  personal_access_token: ""
""")

        ctx = {
            "config": None,
            "environment": None,  # Use default (no environment)
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="validate"),
        }

        exit_code = config_cmd.handle(ctx)

        # Should fail due to placeholder value
        assert exit_code == 1

    def test_config_validate_with_warnings(self, tmp_path, monkeypatch):
        """Test validation succeeds with warnings."""
        # Create temp config directory
        config_dir = tmp_path / "epymodelingsuite-cloud"
        config_dir.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Write config with valid values but placeholder GitHub token
        config_file = config_dir / "config.yaml"
        config_file.write_text("""
storage:
  dir_prefix: pipeline/test/
google_cloud:
  project_id: my-project
  region: us-central1
  bucket_name: my-bucket
docker:
  registry: us-central1-docker.pkg.dev
  repo_name: epymodelingsuite-repo
  image_name: epymodelingsuite
  image_tag: latest
github:
  personal_access_token: ghp_xxxxxxxxxxxxxxxxxxxx  # Placeholder token
  forecast_repo: org/repo
  modeling_suite_repo: org/suite
  modeling_suite_ref: main
""")

        ctx = {
            "config": None,
            "environment": "test",  # Provide environment for templating
            "profile": "test",  # Provide profile for templating
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="validate"),
        }

        exit_code = config_cmd.handle(ctx)

        # Should succeed but with warning about GitHub token
        assert exit_code == 0

    def test_config_validate_load_error(self, tmp_path, monkeypatch):
        """Test validation fails when config cannot be loaded."""
        # Create temp directory WITHOUT config file
        config_dir = tmp_path / "epymodelingsuite-cloud"
        config_dir.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        ctx = {
            "config": None,
            "environment": None,
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="validate"),
        }

        exit_code = config_cmd.handle(ctx)

        # Should fail due to missing config file
        assert exit_code == 1


class TestConfigPathCommand:
    """Test config path command."""

    @patch("epycloud.commands.config_cmd.operations.get_config_dir")
    def test_config_path_displays_directory(self, mock_get_dir):
        """Test that path displays config directory."""
        mock_get_dir.return_value = Path("/home/user/.config/epymodelingsuite-cloud")

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="path"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0


class TestConfigGetCommand:
    """Test config get command."""

    def test_config_get_nested_value(self, mock_config):
        """Test getting nested config value with dot notation."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="get", key="google_cloud.project_id"),
        }

        with patch("epycloud.commands.config_cmd.handlers.get_config_value") as mock_get:
            mock_get.return_value = "test-project"
            exit_code = config_cmd.handle(ctx)

            assert exit_code == 0
            mock_get.assert_called_once_with(mock_config, "google_cloud.project_id")

    def test_config_get_key_not_found(self, mock_config):
        """Test error when key is not found."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="get", key="nonexistent.key"),
        }

        with patch("epycloud.commands.config_cmd.handlers.get_config_value") as mock_get:
            mock_get.return_value = None
            exit_code = config_cmd.handle(ctx)

            assert exit_code == 1

    def test_config_get_top_level_value(self, mock_config):
        """Test getting top-level config value."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="get", key="docker"),
        }

        with patch("epycloud.commands.config_cmd.handlers.get_config_value") as mock_get:
            mock_get.return_value = mock_config["docker"]
            exit_code = config_cmd.handle(ctx)

            assert exit_code == 0


class TestConfigSetCommand:
    """Test config set command."""

    @patch("epycloud.commands.config_cmd.operations.get_config_file")
    @patch("epycloud.commands.config_cmd.handlers.set_config_value")
    def test_config_set_value(self, mock_set_value, mock_get_file, tmp_path):
        """Test setting config value."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("google_cloud:\n  project_id: old-project\n")
        mock_get_file.return_value = config_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                config_subcommand="set", key="google_cloud.project_id", value="new-project"
            ),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0
        mock_set_value.assert_called_once()

    def test_config_set_file_not_found(self, tmp_path, monkeypatch):
        """Test error when config file doesn't exist."""
        # Create temp directory WITHOUT config file
        config_dir = tmp_path / "epymodelingsuite-cloud"
        config_dir.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Verify no config.yaml exists
        config_file = config_dir / "config.yaml"
        assert not config_file.exists(), "Config file should not exist for this test"

        ctx = {
            "config": None,
            "environment": None,
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="set", key="some.key", value="value"),
        }

        exit_code = config_cmd.handle(ctx)

        # Should fail due to missing config file
        assert exit_code == 1

    @patch("epycloud.commands.config_cmd.operations.get_config_file")
    @patch("epycloud.commands.config_cmd.handlers.set_config_value")
    def test_config_set_creates_nested_key(self, mock_set_value, mock_get_file, tmp_path):
        """Test setting a new nested key."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("google_cloud:\n  project_id: test\n")
        mock_get_file.return_value = config_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                config_subcommand="set", key="new_section.new_key", value="new_value"
            ),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0
        mock_set_value.assert_called_once()


class TestConfigListEnvsCommand:
    """Test config list-envs command."""

    @patch("epycloud.commands.config_cmd.handlers.list_environments")
    def test_config_list_envs_shows_available(self, mock_list_envs):
        """Test listing available environments."""
        mock_list_envs.return_value = ["dev", "prod", "local"]

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="list-envs"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.config_cmd.handlers.list_environments")
    def test_config_list_envs_marks_current(self, mock_list_envs):
        """Test that current environment is marked."""
        mock_list_envs.return_value = ["dev", "prod", "local"]

        ctx = {
            "config": None,
            "environment": "prod",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="list-envs"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.config_cmd.handlers.list_environments")
    def test_config_list_envs_empty(self, mock_list_envs):
        """Test handling empty environment list."""
        mock_list_envs.return_value = []

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="list-envs"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 0


class TestConfigNoSubcommand:
    """Test config command without subcommand."""

    def test_config_no_subcommand_prints_help(self):
        """Test that no subcommand prints help."""
        mock_parser = Mock()

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand=None, _config_parser=mock_parser),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 1
        mock_parser.print_help.assert_called_once()

    def test_config_unknown_subcommand(self):
        """Test error for unknown subcommand."""
        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(config_subcommand="unknown"),
        }

        exit_code = config_cmd.handle(ctx)

        assert exit_code == 1
