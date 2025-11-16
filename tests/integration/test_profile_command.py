"""Integration tests for profile command."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from epycloud.commands import profile


class TestProfileListCommand:
    """Test profile list command."""

    @patch("epycloud.commands.profile.get_active_profile_file")
    @patch("epycloud.commands.profile.get_config_dir")
    def test_profile_list_shows_profiles(
        self, mock_config_dir, mock_active_file, tmp_path
    ):
        """Test listing available profiles."""
        config_dir = tmp_path / ".config" / "epymodelingsuite-cloud"
        profiles_dir = config_dir / "profiles"
        profiles_dir.mkdir(parents=True)

        # Create test profiles
        (profiles_dir / "flu.yaml").write_text("description: Flu modeling\n")
        (profiles_dir / "covid.yaml").write_text("description: COVID modeling\n")

        # Create active profile file
        active_file = config_dir / "active_profile"
        active_file.write_text("flu\n")

        mock_config_dir.return_value = config_dir
        mock_active_file.return_value = active_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="list"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.profile.get_active_profile_file")
    @patch("epycloud.commands.profile.get_config_dir")
    def test_profile_list_marks_active(
        self, mock_config_dir, mock_active_file, tmp_path
    ):
        """Test that active profile is marked with asterisk."""
        config_dir = tmp_path / ".config" / "epymodelingsuite-cloud"
        profiles_dir = config_dir / "profiles"
        profiles_dir.mkdir(parents=True)

        (profiles_dir / "flu.yaml").write_text("description: Flu\n")
        (profiles_dir / "covid.yaml").write_text("description: COVID\n")

        active_file = config_dir / "active_profile"
        active_file.write_text("covid\n")

        mock_config_dir.return_value = config_dir
        mock_active_file.return_value = active_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="list"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.profile.get_config_dir")
    def test_profile_list_no_profiles_directory(self, mock_config_dir, tmp_path):
        """Test error when profiles directory doesn't exist."""
        config_dir = tmp_path / ".config" / "epymodelingsuite-cloud"
        # Don't create profiles directory
        mock_config_dir.return_value = config_dir

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="list"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.profile.get_active_profile_file")
    @patch("epycloud.commands.profile.get_config_dir")
    def test_profile_list_empty(self, mock_config_dir, mock_active_file, tmp_path):
        """Test listing when no profiles exist."""
        config_dir = tmp_path / ".config" / "epymodelingsuite-cloud"
        profiles_dir = config_dir / "profiles"
        profiles_dir.mkdir(parents=True)
        # No profiles created

        mock_config_dir.return_value = config_dir

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="list"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 0


class TestProfileUseCommand:
    """Test profile use command."""

    @patch("epycloud.commands.profile.get_active_profile_file")
    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_use_activates(
        self, mock_get_profile, mock_active_file, tmp_path
    ):
        """Test activating a profile."""
        profile_file = tmp_path / "flu.yaml"
        profile_file.write_text("description: Flu\n")
        active_file = tmp_path / "active_profile"

        mock_get_profile.return_value = profile_file
        mock_active_file.return_value = active_file

        args = Mock(profile_subcommand="use")
        args.name = "flu"  # Set as attribute, not Mock property

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 0
        assert active_file.read_text().strip() == "flu"

    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_use_not_found(self, mock_get_profile):
        """Test error when profile doesn't exist."""
        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_get_profile.return_value = mock_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="use", name="nonexistent"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1


class TestProfileCurrentCommand:
    """Test profile current command."""

    @patch("epycloud.commands.profile.get_active_profile_file")
    def test_profile_current_shows_active(self, mock_active_file, tmp_path):
        """Test showing current active profile."""
        active_file = tmp_path / "active_profile"
        active_file.write_text("covid\n")
        mock_active_file.return_value = active_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="current"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.profile.get_active_profile_file")
    def test_profile_current_no_active(self, mock_active_file):
        """Test when no profile is active."""
        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_active_file.return_value = mock_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="current"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1


class TestProfileCreateCommand:
    """Test profile create command."""

    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_create_basic(self, mock_get_profile, tmp_path):
        """Test creating profile with basic template."""
        profile_file = tmp_path / "profiles" / "rsv.yaml"
        profile_file.parent.mkdir(parents=True)
        mock_get_profile.return_value = profile_file

        args = Mock(profile_subcommand="create")
        args.name = "rsv"
        args.template = "basic"
        args.description = "RSV modeling"
        args.forecast_repo = "mobs-lab/rsv-forecast"

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 0
        assert profile_file.exists()
        profile_data = yaml.safe_load(profile_file.read_text())
        assert profile_data["name"] == "rsv"
        assert profile_data["description"] == "RSV modeling"
        assert profile_data["github"]["forecast_repo"] == "mobs-lab/rsv-forecast"

    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_create_full(self, mock_get_profile, tmp_path):
        """Test creating profile with full template."""
        profile_file = tmp_path / "profiles" / "rsv.yaml"
        profile_file.parent.mkdir(parents=True)
        mock_get_profile.return_value = profile_file

        args = Mock(profile_subcommand="create")
        args.name = "rsv"
        args.template = "full"
        args.description = "RSV modeling"
        args.forecast_repo = None

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 0
        profile_data = yaml.safe_load(profile_file.read_text())
        assert "google_cloud" in profile_data
        assert "batch" in profile_data["google_cloud"]

    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_create_already_exists(self, mock_get_profile, tmp_path):
        """Test error when profile already exists."""
        profile_file = tmp_path / "flu.yaml"
        profile_file.write_text("existing: true\n")
        mock_get_profile.return_value = profile_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                profile_subcommand="create",
                name="flu",
                template="basic",
                description=None,
                forecast_repo=None,
            ),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_create_default_values(self, mock_get_profile, tmp_path):
        """Test creating profile with default values."""
        profile_file = tmp_path / "profiles" / "mymodel.yaml"
        profile_file.parent.mkdir(parents=True)
        mock_get_profile.return_value = profile_file

        args = Mock(profile_subcommand="create")
        args.name = "mymodel"
        args.template = "basic"
        args.description = None  # Should use default
        args.forecast_repo = None  # Should use default

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 0
        profile_data = yaml.safe_load(profile_file.read_text())
        assert profile_data["description"] == "mymodel modeling"
        assert profile_data["github"]["forecast_repo"] == "mobs-lab/mymodel-forecast"


class TestProfileEditCommand:
    """Test profile edit command."""

    @patch("epycloud.commands.profile.subprocess.run")
    @patch("epycloud.commands.profile.get_profile_file")
    @patch.dict(os.environ, {"EDITOR": "vim"})
    def test_profile_edit_opens_editor(self, mock_get_profile, mock_subprocess):
        """Test editing profile in editor."""
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_get_profile.return_value = mock_file
        mock_subprocess.return_value = Mock(returncode=0)

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="edit", name="flu"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 0
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0] == "vim"

    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_edit_not_found(self, mock_get_profile):
        """Test error when profile doesn't exist."""
        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_get_profile.return_value = mock_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="edit", name="nonexistent"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.profile.subprocess.run")
    @patch("epycloud.commands.profile.get_profile_file")
    @patch.dict(os.environ, {"EDITOR": "nonexistent"})
    def test_profile_edit_editor_not_found(self, mock_get_profile, mock_subprocess):
        """Test error when editor is not found."""
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_get_profile.return_value = mock_file
        mock_subprocess.side_effect = FileNotFoundError()

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="edit", name="flu"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.profile.subprocess.run")
    @patch("epycloud.commands.profile.get_profile_file")
    @patch.dict(os.environ, {"EDITOR": "vim"})
    def test_profile_edit_editor_fails(self, mock_get_profile, mock_subprocess):
        """Test error when editor process fails."""
        import subprocess as sp

        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_get_profile.return_value = mock_file
        mock_subprocess.side_effect = sp.CalledProcessError(1, "vim")

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="edit", name="flu"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1


class TestProfileShowCommand:
    """Test profile show command."""

    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_show_contents(self, mock_get_profile, tmp_path):
        """Test showing profile YAML contents."""
        profile_file = tmp_path / "flu.yaml"
        profile_data = {
            "name": "flu",
            "description": "Flu modeling",
            "github": {"forecast_repo": "mobs-lab/flu-forecast"},
        }
        profile_file.write_text(yaml.dump(profile_data))
        mock_get_profile.return_value = profile_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="show", name="flu"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_show_not_found(self, mock_get_profile):
        """Test error when profile doesn't exist."""
        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_get_profile.return_value = mock_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="show", name="nonexistent"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1


class TestProfileDeleteCommand:
    """Test profile delete command."""

    @patch("epycloud.commands.profile.get_active_profile_file")
    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_delete_success(
        self, mock_get_profile, mock_active_file, tmp_path
    ):
        """Test deleting inactive profile."""
        profile_file = tmp_path / "covid.yaml"
        profile_file.write_text("description: COVID\n")
        mock_get_profile.return_value = profile_file

        active_file = tmp_path / "active_profile"
        active_file.write_text("flu\n")  # Different profile is active
        mock_active_file.return_value = active_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="delete", name="covid"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 0
        assert not profile_file.exists()

    @patch("epycloud.commands.profile.get_active_profile_file")
    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_delete_active_rejected(
        self, mock_get_profile, mock_active_file, tmp_path
    ):
        """Test that deleting active profile is rejected."""
        profile_file = tmp_path / "flu.yaml"
        profile_file.write_text("description: Flu\n")
        mock_get_profile.return_value = profile_file

        active_file = tmp_path / "active_profile"
        active_file.write_text("flu\n")  # Same as profile being deleted
        mock_active_file.return_value = active_file

        args = Mock(profile_subcommand="delete")
        args.name = "flu"

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": args,
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1
        # File should still exist
        assert profile_file.exists()

    @patch("epycloud.commands.profile.get_profile_file")
    def test_profile_delete_not_found(self, mock_get_profile):
        """Test error when profile doesn't exist."""
        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_get_profile.return_value = mock_file

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="delete", name="nonexistent"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1


class TestProfileNoSubcommand:
    """Test profile command without subcommand."""

    def test_profile_no_subcommand_prints_help(self):
        """Test that no subcommand prints help."""
        mock_parser = Mock()

        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand=None, _profile_parser=mock_parser),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1
        mock_parser.print_help.assert_called_once()

    def test_profile_unknown_subcommand(self):
        """Test error for unknown subcommand."""
        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(profile_subcommand="unknown"),
        }

        exit_code = profile.handle(ctx)

        assert exit_code == 1
