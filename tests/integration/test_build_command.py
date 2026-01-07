"""Integration tests for build command."""

import json
from pathlib import Path
from unittest.mock import Mock, patch, call

import pytest

from epycloud.commands import build


class TestBuildCloudCommand:
    """Test build cloud command."""

    @patch("epycloud.commands.build.cloud.ask_confirmation")
    @patch("epycloud.lib.command_helpers.get_project_root")
    @patch("epycloud.commands.build.cloud.subprocess.run")
    def test_build_cloud_success(
        self, mock_subprocess, mock_root, mock_confirm, mock_config
    ):
        """Test successful cloud build submission."""
        mock_root.return_value = Path("/test/project")
        mock_confirm.return_value = True
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Build ID: abc123\n",
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
                build_subcommand="cloud",
                no_cache=False,
                tag=None,
                wait=False,
                dockerfile=None,
                context=None,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called

    @patch("epycloud.commands.build.cloud.ask_confirmation")
    @patch("epycloud.lib.command_helpers.get_project_root")
    @patch("epycloud.commands.build.cloud.subprocess.run")
    def test_build_cloud_with_wait(
        self, mock_subprocess, mock_root, mock_confirm, mock_config
    ):
        """Test cloud build with wait flag."""
        mock_root.return_value = Path("/test/project")
        mock_confirm.return_value = True
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Build completed\n",
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
                build_subcommand="cloud",
                no_cache=False,
                tag=None,
                wait=True,
                dockerfile=None,
                context=None,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.lib.command_helpers.get_project_root")
    def test_build_cloud_dry_run(self, mock_root, mock_config):
        """Test cloud build dry run mode."""
        mock_root.return_value = Path("/test/project")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(
                build_subcommand="cloud",
                no_cache=False,
                tag=None,
                wait=False,
                dockerfile=None,
                context=None,
            ),
        }

        with patch("epycloud.commands.build.cloud.subprocess.run") as mock_subprocess:
            exit_code = build.handle(ctx)

            # Dry run should still succeed but not run subprocess
            assert exit_code == 0

    @patch("epycloud.commands.build.cloud.ask_confirmation")
    @patch("epycloud.lib.command_helpers.get_project_root")
    @patch("epycloud.commands.build.cloud.subprocess.run")
    def test_build_cloud_cancelled(
        self, mock_subprocess, mock_root, mock_confirm, mock_config
    ):
        """Test cloud build cancelled by user."""
        mock_root.return_value = Path("/test/project")
        mock_confirm.return_value = False  # User cancels

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                build_subcommand="cloud",
                no_cache=False,
                tag=None,
                wait=False,
                dockerfile=None,
                context=None,
                cache=False,
            ),
        }

        exit_code = build.handle(ctx)

        # Should exit with 0 when cancelled
        assert exit_code == 0
        # Subprocess should not be called when build is cancelled
        assert not mock_subprocess.called

    def test_build_cloud_missing_project_id(self):
        """Test error when project_id not configured."""
        config = {
            "google_cloud": {
                "region": "us-central1",
                # Missing project_id
            },
            "docker": {
                "repo_name": "test-repo",
                "image_name": "test-image",
                "image_tag": "latest",
            },
            "github": {
                "modeling_suite_repo": "org/repo",
                "modeling_suite_ref": "main",
            },
        }

        ctx = {
            "config": config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                build_subcommand="cloud",
                no_cache=False,
                tag=None,
                wait=False,
                dockerfile=None,
                context=None,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 2

    def test_build_cloud_missing_config(self):
        """Test error when config is missing."""
        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "dry_run": False,
            "args": Mock(build_subcommand="cloud"),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 2


class TestBuildLocalCommand:
    """Test build local command."""

    @patch("epycloud.commands.build.local.ask_confirmation")
    @patch("epycloud.commands.build.handlers.get_github_pat")
    @patch("epycloud.lib.command_helpers.get_project_root")
    @patch("epycloud.commands.build.cloud.subprocess.run")
    def test_build_local_success(
        self, mock_subprocess, mock_root, mock_pat, mock_confirm, mock_config
    ):
        """Test successful local build."""
        mock_root.return_value = Path("/test/project")
        mock_pat.return_value = "ghp_test_token"
        mock_confirm.return_value = True
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Build successful\n",
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
                build_subcommand="local",
                no_cache=False,
                tag=None,
                no_push=False,
                dockerfile=None,
                context=None,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called

    @patch("epycloud.commands.build.handlers.get_github_pat")
    @patch("epycloud.lib.command_helpers.get_project_root")
    def test_build_local_missing_github_pat(self, mock_root, mock_pat, mock_config):
        """Test error when GitHub PAT is missing."""
        mock_root.return_value = Path("/test/project")
        mock_pat.return_value = None  # PAT is missing

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                build_subcommand="local",
                no_cache=False,
                tag=None,
                no_push=False,
                dockerfile=None,
                context=None,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 2

    @patch("epycloud.commands.build.handlers.get_github_pat")
    @patch("epycloud.lib.command_helpers.get_project_root")
    def test_build_local_dry_run(self, mock_root, mock_pat, mock_config):
        """Test local build dry run mode."""
        mock_root.return_value = Path("/test/project")
        mock_pat.return_value = "ghp_test_token"

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(
                build_subcommand="local",
                no_cache=False,
                tag=None,
                no_push=False,
                dockerfile=None,
                context=None,
            ),
        }

        with patch("epycloud.commands.build.local.subprocess.run") as mock_subprocess:
            exit_code = build.handle(ctx)

            assert exit_code == 0


class TestBuildDevCommand:
    """Test build dev command."""

    @patch("epycloud.commands.build.dev.ask_confirmation")
    @patch("epycloud.commands.build.handlers.get_github_pat")
    @patch("epycloud.lib.command_helpers.get_project_root")
    @patch("epycloud.commands.build.cloud.subprocess.run")
    def test_build_dev_success(
        self, mock_subprocess, mock_root, mock_pat, mock_confirm, mock_config
    ):
        """Test successful dev build."""
        mock_root.return_value = Path("/test/project")
        mock_pat.return_value = "ghp_test_token"
        mock_confirm.return_value = True
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Build successful\n",
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
                build_subcommand="dev",
                no_cache=False,
                tag=None,
                push=False,
                dockerfile=None,
                context=None,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called

    @patch("epycloud.commands.build.handlers.get_github_pat")
    @patch("epycloud.lib.command_helpers.get_project_root")
    def test_build_dev_missing_github_pat(self, mock_root, mock_pat, mock_config):
        """Test error when GitHub PAT is missing."""
        mock_root.return_value = Path("/test/project")
        mock_pat.return_value = None  # PAT is missing

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                build_subcommand="dev",
                no_cache=False,
                tag=None,
                push=False,
                dockerfile=None,
                context=None,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 2

    @patch("epycloud.commands.build.handlers.get_github_pat")
    @patch("epycloud.lib.command_helpers.get_project_root")
    def test_build_dev_dry_run(self, mock_root, mock_pat, mock_config):
        """Test dev build dry run mode."""
        mock_root.return_value = Path("/test/project")
        mock_pat.return_value = "ghp_test_token"

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(
                build_subcommand="dev",
                no_cache=False,
                tag=None,
                push=False,
                dockerfile=None,
                context=None,
            ),
        }

        with patch("epycloud.commands.build.dev.subprocess.run") as mock_subprocess:
            exit_code = build.handle(ctx)

            assert exit_code == 0

    @patch("epycloud.commands.build.dev.ask_confirmation")
    @patch("epycloud.commands.build.handlers.get_github_pat")
    @patch("epycloud.lib.command_helpers.get_project_root")
    @patch("epycloud.commands.build.cloud.subprocess.run")
    def test_build_dev_with_custom_tag(
        self, mock_subprocess, mock_root, mock_pat, mock_confirm, mock_config
    ):
        """Test dev build with custom tag."""
        mock_root.return_value = Path("/test/project")
        mock_pat.return_value = "ghp_test_token"
        mock_confirm.return_value = True
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Build successful\n",
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
                build_subcommand="dev",
                no_cache=False,
                tag="my-custom-tag",
                push=False,
                dockerfile=None,
                context=None,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 0


class TestBuildStatusCommand:
    """Test build status command."""

    @patch("epycloud.commands.build.cloud.subprocess.run")
    def test_build_status_display(self, mock_subprocess, mock_config):
        """Test displaying build status."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "id": "build-123",
                        "status": "SUCCESS",
                        "createTime": "2025-11-16T10:00:00Z",
                        "finishTime": "2025-11-16T10:05:00Z",
                        "images": ["us-central1-docker.pkg.dev/project/repo/image:tag"],
                        "source": {
                            "storageSource": {"bucket": "test-bucket", "object": "src.tar.gz"}
                        },
                    },
                    {
                        "id": "build-456",
                        "status": "WORKING",
                        "createTime": "2025-11-16T11:00:00Z",
                        "images": [],
                        "source": {},
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
                build_subcommand="status",
                limit=10,
                ongoing=False,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 0
        assert mock_subprocess.called

    @patch("epycloud.commands.build.cloud.subprocess.run")
    def test_build_status_no_builds(self, mock_subprocess, mock_config):
        """Test handling empty build list."""
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
                build_subcommand="status",
                limit=10,
                ongoing=False,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 0

    @patch("epycloud.commands.build.cloud.subprocess.run")
    def test_build_status_ongoing_only(self, mock_subprocess, mock_config):
        """Test showing only ongoing builds."""
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
                build_subcommand="status",
                limit=10,
                ongoing=True,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 0
        # Verify --ongoing flag was passed
        cmd = mock_subprocess.call_args[0][0]
        assert "--ongoing" in cmd

    @patch("epycloud.commands.build.cloud.subprocess.run")
    def test_build_status_gcloud_error(self, mock_subprocess, mock_config):
        """Test handling gcloud command failure."""
        mock_subprocess.return_value = Mock(
            returncode=1,
            stdout="",
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
                build_subcommand="status",
                limit=10,
                ongoing=False,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 1

    def test_build_status_missing_project_id(self):
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
                build_subcommand="status",
                limit=10,
                ongoing=False,
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 2


class TestBuildNoSubcommand:
    """Test build command without subcommand."""

    def test_build_no_subcommand(self, mock_config):
        """Test error when no subcommand specified."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                build_subcommand=None,
                _build_parser=Mock(print_help=Mock()),
            ),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 1

    def test_build_missing_config(self):
        """Test error when config is missing."""
        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "dry_run": False,
            "args": Mock(build_subcommand="cloud"),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 2

    def test_build_unknown_subcommand(self, mock_config):
        """Test error for unknown subcommand."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(build_subcommand="unknown"),
        }

        exit_code = build.handle(ctx)

        assert exit_code == 1


class TestBuildDisplayStatus:
    """Test build status display formatting."""

    def test_display_build_status_empty(self):
        """Test displaying empty build list."""
        build.display.display_build_status([], 10)

    def test_display_build_status_with_builds(self):
        """Test displaying builds."""
        builds = [
            {
                "id": "build-123",
                "status": "SUCCESS",
                "createTime": "2025-11-16T10:00:00Z",
                "finishTime": "2025-11-16T10:05:00Z",
                "images": ["image:tag"],
                "source": {},
            }
        ]
        # Should not raise an error
        build.display.display_build_status(builds, 10)

    def test_display_build_status_missing_fields(self):
        """Test displaying builds with missing fields."""
        builds = [
            {
                "id": "build-123",
                "status": "WORKING",
                # Missing other fields
            }
        ]
        # Should handle gracefully
        build.display.display_build_status(builds, 10)
