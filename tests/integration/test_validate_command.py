"""Integration tests for validate command."""

import json
from unittest.mock import Mock, patch

import pytest
import yaml as yaml_module

from epycloud.commands import validate


class TestValidateLocalCommand:
    """Test validate command with local paths."""

    @patch("epycloud.commands.validate.handlers.validate_directory")
    @patch("epycloud.commands.validate.handlers.validate_local_path")
    def test_validate_local_single_path_text(
        self, mock_validate_path, mock_validate_dir, mock_config, tmp_path
    ):
        """Test validate with single local path and text output."""
        local_path = tmp_path / "config"
        mock_validate_path.return_value = local_path
        mock_validate_dir.return_value = {
            "directory": str(local_path),
            "config_sets": [
                {
                    "basemodel": "basemodel.yaml",
                    "modelset": "sampling.yaml",
                    "status": "pass",
                }
            ],
        }

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=[local_path],
                exp_id=None,
                format="text",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 0
        mock_validate_dir.assert_called_once()

    @patch("epycloud.commands.validate.handlers.validate_directory")
    @patch("epycloud.commands.validate.handlers.validate_local_path")
    def test_validate_local_single_path_json(
        self, mock_validate_path, mock_validate_dir, mock_config, tmp_path, capsys
    ):
        """Test validate with single local path and JSON output."""
        local_path = tmp_path / "config"
        mock_validate_path.return_value = local_path
        result = {
            "directory": str(local_path),
            "config_sets": [
                {
                    "basemodel": "basemodel.yaml",
                    "modelset": "sampling.yaml",
                    "status": "pass",
                }
            ],
        }
        mock_validate_dir.return_value = result

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=[local_path],
                exp_id=None,
                format="json",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "pass"
        assert len(output["config_sets"]) == 1

    @patch("epycloud.commands.validate.handlers.validate_directory")
    @patch("epycloud.commands.validate.handlers.validate_local_path")
    def test_validate_local_multiple_paths(
        self, mock_validate_path, mock_validate_dir, mock_config, tmp_path, capsys
    ):
        """Test validate with multiple local paths."""
        path1 = tmp_path / "config1"
        path2 = tmp_path / "config2"
        mock_validate_path.side_effect = [path1, path2]
        mock_validate_dir.side_effect = [
            {
                "directory": str(path1),
                "config_sets": [
                    {
                        "basemodel": "basemodel.yaml",
                        "modelset": "sampling.yaml",
                        "status": "pass",
                    }
                ],
            },
            {
                "directory": str(path2),
                "config_sets": [
                    {
                        "basemodel": "basemodel.yaml",
                        "modelset": "calibration.yaml",
                        "status": "pass",
                    }
                ],
            },
        ]

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=[path1, path2],
                exp_id=None,
                format="text",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "[PASSED]" in captured.out

    @patch("epycloud.commands.validate.handlers.validate_directory")
    @patch("epycloud.commands.validate.handlers.validate_local_path")
    def test_validate_local_with_failures(
        self, mock_validate_path, mock_validate_dir, mock_config, tmp_path, capsys
    ):
        """Test validate with validation failures."""
        local_path = tmp_path / "config"
        mock_validate_path.return_value = local_path
        mock_validate_dir.return_value = {
            "directory": str(local_path),
            "config_sets": [
                {
                    "basemodel": "basemodel.yaml",
                    "modelset": "sampling.yaml",
                    "status": "fail",
                    "error": "Invalid configuration",
                }
            ],
        }

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=[local_path],
                exp_id=None,
                format="text",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.validate.handlers.validate_local_path")
    def test_validate_local_invalid_path(
        self, mock_validate_path, mock_config, tmp_path
    ):
        """Test validate with invalid local path."""
        from epycloud.exceptions import ValidationError

        mock_validate_path.side_effect = ValidationError("Path does not exist")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=[tmp_path / "nonexistent"],
                exp_id=None,
                format="text",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 1


class TestValidateRemoteCommand:
    """Test validate command with remote GitHub repositories."""

    @patch("epycloud.commands.validate.handlers.validate_remote")
    @patch("epycloud.commands.validate.handlers.validate_exp_id")
    @patch("epycloud.commands.validate.handlers.get_github_config")
    def test_validate_remote_single_exp_id_text(
        self, mock_get_github_config, mock_validate_exp_id, mock_validate_remote, mock_config
    ):
        """Test validate with single exp-id and text output."""
        mock_validate_exp_id.return_value = "test-exp"
        mock_validate_remote.return_value = {
            "directory": "test-org/test-repo/experiments/test-exp/config",
            "config_sets": [
                {
                    "basemodel": "basemodel.yaml",
                    "modelset": "sampling.yaml",
                    "status": "pass",
                }
            ],
        }

        # Mock GitHub config
        mock_get_github_config.return_value = {
            "forecast_repo": "test-org/test-repo",
            "personal_access_token": "github_pat_test_token",
        }

        config = mock_config.copy()

        ctx = {
            "config": config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=None,
                exp_id=["test-exp"],
                format="text",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 0
        mock_validate_remote.assert_called_once()

    @patch("epycloud.commands.validate.handlers.validate_remote")
    @patch("epycloud.commands.validate.handlers.validate_exp_id")
    @patch("epycloud.commands.validate.handlers.get_github_config")
    def test_validate_remote_single_exp_id_json(
        self, mock_get_github_config, mock_validate_exp_id, mock_validate_remote, mock_config, capsys
    ):
        """Test validate with single exp-id and JSON output."""
        mock_validate_exp_id.return_value = "test-exp"
        result = {
            "directory": "test-org/test-repo/experiments/test-exp/config",
            "config_sets": [
                {
                    "basemodel": "basemodel.yaml",
                    "modelset": "sampling.yaml",
                    "status": "pass",
                }
            ],
        }
        mock_validate_remote.return_value = result

        # Mock GitHub config
        mock_get_github_config.return_value = {
            "forecast_repo": "test-org/test-repo",
            "personal_access_token": "github_pat_test_token",
        }

        config = mock_config.copy()

        ctx = {
            "config": config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=None,
                exp_id=["test-exp"],
                format="json",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "pass"

    @patch("epycloud.commands.validate.handlers.expand_exp_id_pattern")
    @patch("epycloud.commands.validate.handlers.validate_remote")
    @patch("epycloud.commands.validate.handlers.get_github_config")
    def test_validate_remote_with_pattern(
        self, mock_get_github_config, mock_validate_remote, mock_expand_pattern, mock_config, capsys
    ):
        """Test validate with exp-id pattern expansion."""
        mock_expand_pattern.return_value = ["test-exp-1", "test-exp-2"]
        mock_validate_remote.side_effect = [
            {
                "directory": "test-org/test-repo/experiments/test-exp-1/config",
                "config_sets": [
                    {
                        "basemodel": "basemodel.yaml",
                        "modelset": "sampling.yaml",
                        "status": "pass",
                    }
                ],
            },
            {
                "directory": "test-org/test-repo/experiments/test-exp-2/config",
                "config_sets": [
                    {
                        "basemodel": "basemodel.yaml",
                        "modelset": "sampling.yaml",
                        "status": "pass",
                    }
                ],
            },
        ]

        # Mock GitHub config
        mock_get_github_config.return_value = {
            "forecast_repo": "test-org/test-repo",
            "personal_access_token": "github_pat_test_token",
        }

        config = mock_config.copy()

        ctx = {
            "config": config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=None,
                exp_id=["test-*"],
                format="text",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 0
        mock_expand_pattern.assert_called_once()

    @patch("epycloud.commands.validate.handlers.validate_remote")
    @patch("epycloud.commands.validate.handlers.validate_exp_id")
    @patch("epycloud.commands.validate.handlers.get_github_config")
    def test_validate_remote_multiple_exp_ids_json(
        self, mock_get_github_config, mock_validate_exp_id, mock_validate_remote, mock_config, capsys
    ):
        """Test validate with multiple exp-ids and JSON output."""
        mock_validate_exp_id.side_effect = ["exp-1", "exp-2"]
        mock_validate_remote.side_effect = [
            {
                "directory": "test-org/test-repo/experiments/exp-1/config",
                "config_sets": [
                    {
                        "basemodel": "basemodel.yaml",
                        "modelset": "sampling.yaml",
                        "status": "pass",
                    }
                ],
            },
            {
                "directory": "test-org/test-repo/experiments/exp-2/config",
                "config_sets": [
                    {
                        "basemodel": "basemodel.yaml",
                        "modelset": "calibration.yaml",
                        "status": "fail",
                        "error": "Validation error",
                    }
                ],
            },
        ]

        # Mock GitHub config
        mock_get_github_config.return_value = {
            "forecast_repo": "test-org/test-repo",
            "personal_access_token": "github_pat_test_token",
        }

        config = mock_config.copy()

        ctx = {
            "config": config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=None,
                exp_id=["exp-1", "exp-2"],
                format="json",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 1  # At least one failed
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["summary"]["total"] == 2
        assert output["summary"]["passed"] == 1
        assert output["summary"]["failed"] == 1

    def test_validate_remote_no_github_token(self, mock_config):
        """Test validate remote without GitHub token."""
        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=None,
                exp_id=["test-exp"],
                format="text",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 2  # Config error

    @patch("epycloud.commands.validate.handlers.validate_github_token")
    def test_validate_remote_with_github_token_arg(
        self, mock_validate_token, mock_config
    ):
        """Test validate remote with --github-token argument."""
        from epycloud.exceptions import ValidationError

        mock_validate_token.side_effect = ValidationError("Invalid token")

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=None,
                exp_id=["test-exp"],
                format="text",
                github_token="invalid-token",
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 1

    @patch("epycloud.commands.validate.handlers.get_github_config")
    def test_validate_remote_no_forecast_repo(self, mock_get_github_config, mock_config):
        """Test validate remote without forecast_repo configured."""
        # Mock GitHub config with no forecast_repo
        mock_get_github_config.return_value = {
            "forecast_repo": None,
            "personal_access_token": "github_pat_test_token",
        }

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=None,
                exp_id=["test-exp"],
                format="text",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 2  # Config error


class TestValidateDryRun:
    """Test validate command with dry-run flag."""

    @patch("epycloud.commands.validate.handlers.validate_directory")
    @patch("epycloud.commands.validate.handlers.validate_local_path")
    def test_validate_local_dry_run(
        self, mock_validate_path, mock_validate_dir, mock_config, tmp_path
    ):
        """Test validate local with dry-run."""
        local_path = tmp_path / "config"
        mock_validate_path.return_value = local_path

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(
                path=[local_path],
                exp_id=None,
                format="text",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 0
        # validate_directory should not be called in dry-run
        mock_validate_dir.assert_not_called()

    @patch("epycloud.commands.validate.handlers.validate_exp_id")
    @patch("epycloud.commands.validate.handlers.get_github_config")
    def test_validate_remote_dry_run(self, mock_get_github_config, mock_validate_exp_id, mock_config):
        """Test validate remote with dry-run."""
        mock_validate_exp_id.return_value = "test-exp"

        # Mock GitHub config
        mock_get_github_config.return_value = {
            "forecast_repo": "test-org/test-repo",
            "personal_access_token": "github_pat_test_token",
        }

        config = mock_config.copy()

        ctx = {
            "config": config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": True,
            "args": Mock(
                path=None,
                exp_id=["test-exp"],
                format="text",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 0


class TestValidateOutputFormats:
    """Test validate command with different output formats."""

    @patch("epycloud.commands.validate.handlers.validate_directory")
    @patch("epycloud.commands.validate.handlers.validate_local_path")
    def test_validate_yaml_output(
        self, mock_validate_path, mock_validate_dir, mock_config, tmp_path, capsys
    ):
        """Test validate with YAML output format."""
        local_path = tmp_path / "config"
        mock_validate_path.return_value = local_path
        result = {
            "directory": str(local_path),
            "config_sets": [
                {
                    "basemodel": "basemodel.yaml",
                    "modelset": "sampling.yaml",
                    "status": "pass",
                }
            ],
        }
        mock_validate_dir.return_value = result

        ctx = {
            "config": mock_config,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=[local_path],
                exp_id=None,
                format="yaml",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 0
        captured = capsys.readouterr()
        output = yaml_module.safe_load(captured.out)
        assert output["status"] == "pass"
        assert len(output["config_sets"]) == 1


class TestValidateConfigError:
    """Test validate command with config errors."""

    def test_validate_missing_config(self):
        """Test validate without configuration."""
        ctx = {
            "config": None,
            "environment": "dev",
            "profile": None,
            "verbose": False,
            "quiet": False,
            "dry_run": False,
            "args": Mock(
                path=None,
                exp_id=["test-exp"],
                format="text",
                github_token=None,
            ),
        }

        exit_code = validate.handle(ctx)

        assert exit_code == 2  # Config error


class TestValidateOperations:
    """Test validate operations module."""

    def test_validate_directory_no_yaml_files(self, tmp_path):
        """Test validate_directory with no YAML files."""
        from epycloud.commands.validate.operations import validate_directory

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        result = validate_directory(
            config_dir=config_dir,
            verbose=False,
            quiet=True,
        )

        assert "error" in result
        assert "No YAML files found" in result["error"]

    def test_validate_directory_no_basemodel(self, tmp_path):
        """Test validate_directory with no basemodel configs."""
        from epycloud.commands.validate.operations import validate_directory

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "sampling.yaml").write_text("test: true")

        # Patch where it's imported, not where it's defined
        with patch("epymodelingsuite.utils.config.identify_config_type") as mock_identify:
            mock_identify.return_value = "sampling"

            result = validate_directory(
                config_dir=config_dir,
                verbose=False,
                quiet=True,
            )

            assert "error" in result
            assert "No basemodel configs found" in result["error"]

    def test_validate_directory_no_modelset(self, tmp_path):
        """Test validate_directory with no modelset configs."""
        from epycloud.commands.validate.operations import validate_directory

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "basemodel.yaml").write_text("test: true")

        # Patch where it's imported, not where it's defined
        with patch("epymodelingsuite.utils.config.identify_config_type") as mock_identify:
            mock_identify.return_value = "basemodel"

            result = validate_directory(
                config_dir=config_dir,
                verbose=False,
                quiet=True,
            )

            assert "error" in result
            assert "No modelset configs found" in result["error"]

    def test_validate_directory_no_epymodelingsuite(self, tmp_path):
        """Test validate_directory without epymodelingsuite package."""
        from epycloud.commands.validate.operations import validate_directory

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Patch the import to raise ImportError
        with patch.dict("sys.modules", {"epymodelingsuite.utils.config": None}):
            result = validate_directory(
                config_dir=config_dir,
                verbose=False,
                quiet=True,
            )

            # Should handle gracefully when package not available
            assert "error" in result
            assert "epymodelingsuite" in result["error"]

    @patch("epycloud.commands.validate.operations.requests.get")
    def test_fetch_config_files_404(self, mock_get):
        """Test fetch_config_files with 404 error."""
        from epycloud.commands.validate.operations import fetch_config_files
        import requests

        mock_response = Mock()
        mock_response.status_code = 404
        # Create a proper HTTPError with response
        http_error = requests.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Config directory not found"):
            fetch_config_files(
                forecast_repo="test-org/test-repo",
                exp_id="test-exp",
                github_token="test-token",
                verbose=False,
                quiet=True,
            )

    @patch("epycloud.commands.validate.operations.requests.get")
    def test_expand_exp_id_pattern_no_wildcards(self, mock_get):
        """Test expand_exp_id_pattern without wildcards."""
        from epycloud.commands.validate.operations import expand_exp_id_pattern

        result = expand_exp_id_pattern(
            pattern="test-exp",
            forecast_repo="test-org/test-repo",
            github_token="test-token",
            verbose=False,
        )

        assert result == ["test-exp"]
        # Should not make API calls
        mock_get.assert_not_called()

    @patch("epycloud.commands.validate.operations.requests.get")
    def test_expand_exp_id_pattern_simple(self, mock_get):
        """Test expand_exp_id_pattern with simple wildcard."""
        from epycloud.commands.validate.operations import expand_exp_id_pattern

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "test-exp-1", "type": "dir"},
            {"name": "test-exp-2", "type": "dir"},
            {"name": "other-exp", "type": "dir"},
        ]
        mock_get.return_value = mock_response

        result = expand_exp_id_pattern(
            pattern="test-*",
            forecast_repo="test-org/test-repo",
            github_token="test-token",
            verbose=False,
        )

        assert "test-exp-1" in result
        assert "test-exp-2" in result
        assert "other-exp" not in result

    @patch("epycloud.commands.validate.operations.requests.get")
    def test_expand_exp_id_pattern_no_matches(self, mock_get):
        """Test expand_exp_id_pattern with no matches."""
        from epycloud.commands.validate.operations import expand_exp_id_pattern

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "other-exp", "type": "dir"},
        ]
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="No experiments match pattern"):
            expand_exp_id_pattern(
                pattern="test-*",
                forecast_repo="test-org/test-repo",
                github_token="test-token",
                verbose=False,
            )
