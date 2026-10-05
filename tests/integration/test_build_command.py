"""Integration tests for build command."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch, call

import pytest

from epycloud.cli import create_parser
from epycloud.commands import build
from epycloud.commands.build import cloud
from epycloud.lib.command_helpers import get_image_uri


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

    @patch("epycloud.commands.build.local.ask_confirmation")
    @patch("epycloud.commands.build.handlers.get_github_pat")
    @patch("epycloud.lib.command_helpers.get_project_root")
    @patch("epycloud.commands.build.local.subprocess.run")
    def test_build_local_without_github_pat(
        self, mock_subprocess, mock_root, mock_pat, mock_confirm, mock_config
    ):
        """Build proceeds without a PAT (public modeling suite) and omits the build arg."""
        mock_root.return_value = Path("/test/project")
        mock_pat.return_value = None
        mock_confirm.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

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
        cmd = mock_subprocess.call_args[0][0]
        assert not any("GITHUB_PAT" in arg for arg in cmd)

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

    @patch("epycloud.commands.build.dev.ask_confirmation")
    @patch("epycloud.commands.build.handlers.get_github_pat")
    @patch("epycloud.lib.command_helpers.get_project_root")
    @patch("epycloud.commands.build.dev.subprocess.run")
    def test_build_dev_without_github_pat(
        self, mock_subprocess, mock_root, mock_pat, mock_confirm, mock_config
    ):
        """Build proceeds without a PAT (public modeling suite) and omits the build arg."""
        mock_root.return_value = Path("/test/project")
        mock_pat.return_value = None
        mock_confirm.return_value = True
        mock_subprocess.return_value = Mock(returncode=0)

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
        cmd = mock_subprocess.call_args[0][0]
        assert not any("GITHUB_PAT" in arg for arg in cmd)

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


class TestBuildReplicationCommand:
    """Test digest-preserving regional image replication."""

    @staticmethod
    def _config_with_regions(mock_config):
        """Return a test config with both regional registries enabled."""
        config = deepcopy(mock_config)
        config["google_cloud"]["batch_regions"] = {
            "us-central1": {"subnet_cidr": "10.0.0.0/20"},
            "us-east5": {"subnet_cidr": "10.1.0.0/20"},
        }
        return config

    def test_parser_exposes_replication_commands(self):
        """The CLI must parse source, destination, and verification commands."""
        replicate = create_parser().parse_args(
            [
                "build",
                "replicate",
                "--from",
                "us-central1",
                "--to",
                "us-east5",
                "--tag",
                "dev",
            ]
        )
        verify = create_parser().parse_args(
            ["build", "verify-replicas", "--tag", "dev"]
        )

        assert replicate.source_region == "us-central1"
        assert replicate.destination_region == "us-east5"
        assert replicate.tag == "dev"
        assert verify.tag == "dev"

    @patch("epycloud.commands.build.handlers.get_project_root")
    @patch("epycloud.commands.build.handlers.cloud.replicate_image")
    def test_replicate_uses_only_configured_regions(
        self, mock_replicate, mock_root, mock_config
    ):
        """A valid request must pass its exact regional endpoints to Cloud Build."""
        config = self._config_with_regions(mock_config)
        mock_root.return_value = Path("/test/project")
        mock_replicate.return_value = 0
        ctx = {
            "config": config,
            "verbose": False,
            "dry_run": False,
            "args": Mock(
                build_subcommand="replicate",
                source_region="us-central1",
                destination_region="us-east5",
                tag="dev",
            ),
        }

        assert build.handle(ctx) == 0
        assert mock_replicate.call_args.kwargs["source_region"] == "us-central1"
        assert mock_replicate.call_args.kwargs["destination_region"] == "us-east5"
        assert mock_replicate.call_args.kwargs["image_tag"] == "dev"

    def test_replicate_rejects_an_unconfigured_region(self, mock_config):
        """Replication cannot create image state outside the Batch region allowlist."""
        config = self._config_with_regions(mock_config)
        ctx = {
            "config": config,
            "verbose": False,
            "dry_run": False,
            "args": Mock(
                build_subcommand="replicate",
                source_region="us-central1",
                destination_region="us-west1",
                tag="dev",
            ),
        }

        assert build.handle(ctx) == 2

    @patch("epycloud.commands.build.handlers.cloud.resolve_image_digest")
    def test_verify_replicas_requires_identical_digests(
        self, mock_resolve, mock_config
    ):
        """Verification must fail when regional tags point at different manifests."""
        config = self._config_with_regions(mock_config)
        mock_resolve.side_effect = ["sha256:" + "a" * 64, "sha256:" + "b" * 64]
        ctx = {
            "config": config,
            "verbose": False,
            "dry_run": False,
            "args": Mock(build_subcommand="verify-replicas", tag="dev"),
        }

        assert build.handle(ctx) == 1

    @patch("epycloud.commands.build.handlers.cloud.resolve_image_digest")
    def test_verify_replicas_accepts_one_digest(self, mock_resolve, mock_config):
        """Verification succeeds only when all configured regions match."""
        config = self._config_with_regions(mock_config)
        digest = "sha256:" + "a" * 64
        mock_resolve.side_effect = [digest, digest]
        ctx = {
            "config": config,
            "verbose": False,
            "dry_run": False,
            "args": Mock(build_subcommand="verify-replicas", tag="dev"),
        }

        assert build.handle(ctx) == 0

    @patch("epycloud.commands.build.cloud.ask_confirmation", return_value=True)
    @patch("epycloud.commands.build.cloud.resolve_image_digest")
    @patch("epycloud.commands.build.cloud.subprocess.run")
    def test_cloud_build_copies_the_resolved_digest_without_source(
        self, mock_subprocess, mock_resolve, _mock_confirm, tmp_path
    ):
        """Cloud Build must copy source@digest and submit without source upload."""
        (tmp_path / "cloudbuild-replicate.yaml").write_text("steps: []\n")
        digest = "sha256:" + "a" * 64
        mock_resolve.return_value = digest
        mock_subprocess.return_value = Mock(returncode=0)

        result = cloud.replicate_image(
            project_id="test-project",
            build_region="us-central1",
            source_region="us-central1",
            destination_region="us-east5",
            repo_name="test-repo",
            image_name="test-image",
            image_tag="dev",
            project_root=tmp_path,
            verbose=False,
            dry_run=False,
        )

        assert result == 0
        command = mock_subprocess.call_args.args[0]
        assert "--no-source" in command
        substitutions = next(
            item for item in command if item.startswith("--substitutions=")
        )
        assert f"_IMAGE_DIGEST={digest}" in substitutions

    def test_image_uri_can_select_a_regional_registry(self, mock_config):
        """A compute-region override must replace only the registry hostname."""
        assert get_image_uri(mock_config, tag="dev", region="us-east5") == (
            "us-east5-docker.pkg.dev/test-project/"
            "epymodelingsuite-repo/epymodelingsuite:dev"
        )
