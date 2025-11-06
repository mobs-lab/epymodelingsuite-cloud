"""Tests for scripts/util/config.py module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from util import config


@pytest.mark.unit
class TestResolveConfigs:
    """Tests for resolve_configs() function."""

    def test_resolve_configs_finds_basemodel(self, temp_local_path):
        """Test resolve_configs finds basemodel config."""
        # Create config directory
        config_dir = temp_local_path / "experiments" / "test-exp" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create basemodel config
        # Note: identify_config_type is mocked, so this YAML isn't actually parsed.
        basemodel_file = config_dir / "basemodel_config.yaml"
        basemodel_file.write_text(
            """
model:
  name: "test_model"
  compartments:
    - id: S
    - id: I
    - id: R
"""
        )

        with patch("util.config.identify_config_type", return_value="basemodel"):
            configs = config.resolve_configs(
                "test-exp", config_dir=str(temp_local_path / "experiments")
            )

        assert configs["basemodel"] is not None
        assert configs["basemodel"].endswith("basemodel_config.yaml")
        assert configs["sampling"] is None
        assert configs["calibration"] is None
        assert configs["output"] is None

    def test_resolve_configs_finds_all_types(self, temp_local_path):
        """Test resolve_configs finds all config types."""
        # Create config directory
        config_dir = temp_local_path / "experiments" / "test-exp" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create different config files
        (config_dir / "basemodel.yaml").write_text("model: {}")
        (config_dir / "sampling.yaml").write_text("sampling: {}")
        (config_dir / "calibration.yaml").write_text("calibration: {}")
        (config_dir / "output.yaml").write_text("output: {}")

        def mock_identify(file_path):
            """Mock identify_config_type based on filename."""
            filename = Path(file_path).name
            if "basemodel" in filename:
                return "basemodel"
            elif "sampling" in filename:
                return "sampling"
            elif "calibration" in filename:
                return "calibration"
            elif "output" in filename:
                return "output"
            return None

        with patch("util.config.identify_config_type", side_effect=mock_identify):
            configs = config.resolve_configs(
                "test-exp", config_dir=str(temp_local_path / "experiments")
            )

        assert configs["basemodel"] is not None
        assert configs["sampling"] is not None
        assert configs["calibration"] is not None
        assert configs["output"] is not None

    def test_resolve_configs_missing_directory(self, temp_local_path):
        """Test resolve_configs raises FileNotFoundError for missing directory."""
        with pytest.raises(FileNotFoundError, match="Config directory not found"):
            config.resolve_configs(
                "nonexistent-exp", config_dir=str(temp_local_path / "experiments")
            )

    def test_resolve_configs_no_yaml_files(self, temp_local_path):
        """Test resolve_configs raises FileNotFoundError when no YAML files exist."""
        # Create empty config directory
        config_dir = temp_local_path / "experiments" / "test-exp" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(FileNotFoundError, match="No YAML files found"):
            config.resolve_configs(
                "test-exp", config_dir=str(temp_local_path / "experiments")
            )

    def test_resolve_configs_duplicate_types(self, temp_local_path):
        """Test resolve_configs raises ValueError for duplicate config types."""
        # Create config directory
        config_dir = temp_local_path / "experiments" / "test-exp" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create two basemodel configs
        (config_dir / "basemodel1.yaml").write_text("model: {}")
        (config_dir / "basemodel2.yaml").write_text("model: {}")

        with patch("util.config.identify_config_type", return_value="basemodel"):
            with pytest.raises(ValueError, match="Multiple basemodel config files found"):
                config.resolve_configs(
                    "test-exp", config_dir=str(temp_local_path / "experiments")
                )

    def test_resolve_configs_handles_unidentified_files(self, temp_local_path, caplog):
        """Test resolve_configs logs warnings for unidentified files."""
        # Create config directory
        config_dir = temp_local_path / "experiments" / "test-exp" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create files
        (config_dir / "basemodel.yaml").write_text("model: {}")
        (config_dir / "unknown.yaml").write_text("random: data")

        def mock_identify(file_path):
            """Mock identify_config_type."""
            filename = Path(file_path).name
            if "basemodel" in filename:
                return "basemodel"
            return None  # Unknown file

        with patch("util.config.identify_config_type", side_effect=mock_identify):
            configs = config.resolve_configs(
                "test-exp", config_dir=str(temp_local_path / "experiments")
            )

        # Should still find basemodel
        assert configs["basemodel"] is not None

        # Should log warning about unidentified file
        assert "Could not identify" in caplog.text
        assert "unknown.yaml" in caplog.text

    def test_resolve_configs_handles_yml_extension(self, temp_local_path):
        """Test resolve_configs handles .yml files (not just .yaml)."""
        # Create config directory
        config_dir = temp_local_path / "experiments" / "test-exp" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create .yml file
        (config_dir / "basemodel.yml").write_text("model: {}")

        with patch("util.config.identify_config_type", return_value="basemodel"):
            configs = config.resolve_configs(
                "test-exp", config_dir=str(temp_local_path / "experiments")
            )

        assert configs["basemodel"] is not None
        assert configs["basemodel"].endswith("basemodel.yml")


@pytest.mark.unit
class TestLoadAllConfigs:
    """Tests for load_all_configs() function."""

    def test_load_all_configs_basemodel_only(self):
        """Test load_all_configs with only basemodel config."""
        config_paths = {
            "basemodel": "/path/to/basemodel.yaml",
            "sampling": None,
            "calibration": None,
            "output": None,
        }

        mock_basemodel = MagicMock()

        with patch(
            "util.config.load_basemodel_config_from_file", return_value=mock_basemodel
        ):
            basemodel, sampling, calibration, output = config.load_all_configs(
                config_paths, validate_consistency=False
            )

        assert basemodel is mock_basemodel
        assert sampling is None
        assert calibration is None
        assert output is None

    def test_load_all_configs_all_types(self):
        """Test load_all_configs with all config types present."""
        config_paths = {
            "basemodel": "/path/to/basemodel.yaml",
            "sampling": "/path/to/sampling.yaml",
            "calibration": "/path/to/calibration.yaml",
            "output": "/path/to/output.yaml",
        }

        mock_basemodel = MagicMock()
        mock_sampling = MagicMock()
        mock_calibration = MagicMock()
        mock_output = MagicMock()

        with patch(
            "util.config.load_basemodel_config_from_file", return_value=mock_basemodel
        ), patch(
            "util.config.load_sampling_config_from_file", return_value=mock_sampling
        ), patch(
            "util.config.load_calibration_config_from_file",
            return_value=mock_calibration,
        ), patch(
            "util.config.load_output_config_from_file", return_value=mock_output
        ), patch(
            "util.config.validate_cross_config_consistency"
        ):
            basemodel, sampling, calibration, output = config.load_all_configs(
                config_paths
            )

        assert basemodel is mock_basemodel
        assert sampling is mock_sampling
        assert calibration is mock_calibration
        assert output is mock_output

    def test_load_all_configs_validates_consistency_with_sampling(self):
        """Test load_all_configs validates consistency when sampling config present."""
        config_paths = {
            "basemodel": "/path/to/basemodel.yaml",
            "sampling": "/path/to/sampling.yaml",
            "calibration": None,
            "output": None,
        }

        mock_basemodel = MagicMock()
        mock_sampling = MagicMock()

        with patch(
            "util.config.load_basemodel_config_from_file", return_value=mock_basemodel
        ), patch(
            "util.config.load_sampling_config_from_file", return_value=mock_sampling
        ), patch(
            "util.config.validate_cross_config_consistency"
        ) as mock_validate:
            config.load_all_configs(config_paths, validate_consistency=True)

        # Should validate configs (basemodel, sampling as modelset, output=None)
        mock_validate.assert_called_once_with(mock_basemodel, mock_sampling, None)

    def test_load_all_configs_validates_consistency_with_calibration(self):
        """Test load_all_configs validates consistency when calibration config present."""
        config_paths = {
            "basemodel": "/path/to/basemodel.yaml",
            "sampling": None,
            "calibration": "/path/to/calibration.yaml",
            "output": None,
        }

        mock_basemodel = MagicMock()
        mock_calibration = MagicMock()

        with patch(
            "util.config.load_basemodel_config_from_file", return_value=mock_basemodel
        ), patch(
            "util.config.load_calibration_config_from_file",
            return_value=mock_calibration,
        ), patch(
            "util.config.validate_cross_config_consistency"
        ) as mock_validate:
            config.load_all_configs(config_paths, validate_consistency=True)

        # Should validate configs (basemodel, calibration as modelset, output=None)
        mock_validate.assert_called_once_with(mock_basemodel, mock_calibration, None)

    def test_load_all_configs_validates_both_when_present(self):
        """Test load_all_configs validates all configs when sampling and calibration present."""
        config_paths = {
            "basemodel": "/path/to/basemodel.yaml",
            "sampling": "/path/to/sampling.yaml",
            "calibration": "/path/to/calibration.yaml",
            "output": None,
        }

        mock_basemodel = MagicMock()
        mock_sampling = MagicMock()
        mock_calibration = MagicMock()

        with patch(
            "util.config.load_basemodel_config_from_file", return_value=mock_basemodel
        ), patch(
            "util.config.load_sampling_config_from_file", return_value=mock_sampling
        ), patch(
            "util.config.load_calibration_config_from_file",
            return_value=mock_calibration,
        ), patch(
            "util.config.validate_cross_config_consistency"
        ) as mock_validate:
            config.load_all_configs(config_paths, validate_consistency=True)

        # Should validate configs (basemodel, sampling as modelset - calibration is ignored, output=None)
        mock_validate.assert_called_once_with(mock_basemodel, mock_sampling, None)

    def test_load_all_configs_validates_with_output_only(self):
        """Test load_all_configs skips validation when only output config is present (no sampling/calibration)."""
        config_paths = {
            "basemodel": "/path/to/basemodel.yaml",
            "sampling": None,
            "calibration": None,
            "output": "/path/to/output.yaml",
        }

        mock_basemodel = MagicMock()
        mock_output = MagicMock()

        with patch(
            "util.config.load_basemodel_config_from_file", return_value=mock_basemodel
        ), patch(
            "util.config.load_output_config_from_file", return_value=mock_output
        ), patch(
            "util.config.validate_cross_config_consistency"
        ) as mock_validate:
            config.load_all_configs(config_paths, validate_consistency=True)

        # Should NOT validate because no sampling/calibration config (validation requires modelset)
        mock_validate.assert_not_called()

    def test_load_all_configs_validates_with_output_config(self):
        """Test load_all_configs validates when output config is present with sampling."""
        config_paths = {
            "basemodel": "/path/to/basemodel.yaml",
            "sampling": "/path/to/sampling.yaml",
            "calibration": None,
            "output": "/path/to/output.yaml",
        }

        mock_basemodel = MagicMock()
        mock_sampling = MagicMock()
        mock_output = MagicMock()

        with patch(
            "util.config.load_basemodel_config_from_file", return_value=mock_basemodel
        ), patch(
            "util.config.load_sampling_config_from_file", return_value=mock_sampling
        ), patch(
            "util.config.load_output_config_from_file", return_value=mock_output
        ), patch(
            "util.config.validate_cross_config_consistency"
        ) as mock_validate:
            config.load_all_configs(config_paths, validate_consistency=True)

        # Should validate configs (basemodel, sampling as modelset, output)
        mock_validate.assert_called_once_with(mock_basemodel, mock_sampling, mock_output)

    def test_load_all_configs_validates_all_four_configs(self):
        """Test load_all_configs validates when all four config types are present."""
        config_paths = {
            "basemodel": "/path/to/basemodel.yaml",
            "sampling": "/path/to/sampling.yaml",
            "calibration": "/path/to/calibration.yaml",
            "output": "/path/to/output.yaml",
        }

        mock_basemodel = MagicMock()
        mock_sampling = MagicMock()
        mock_calibration = MagicMock()
        mock_output = MagicMock()

        with patch(
            "util.config.load_basemodel_config_from_file", return_value=mock_basemodel
        ), patch(
            "util.config.load_sampling_config_from_file", return_value=mock_sampling
        ), patch(
            "util.config.load_calibration_config_from_file",
            return_value=mock_calibration,
        ), patch(
            "util.config.load_output_config_from_file", return_value=mock_output
        ), patch(
            "util.config.validate_cross_config_consistency"
        ) as mock_validate:
            config.load_all_configs(config_paths, validate_consistency=True)

        # Should validate configs (basemodel, sampling as modelset - calibration ignored, output)
        mock_validate.assert_called_once_with(
            mock_basemodel, mock_sampling, mock_output
        )

    def test_load_all_configs_skips_validation_when_disabled(self):
        """Test load_all_configs skips validation when validate_consistency=False."""
        config_paths = {
            "basemodel": "/path/to/basemodel.yaml",
            "sampling": "/path/to/sampling.yaml",
            "calibration": None,
            "output": None,
        }

        mock_basemodel = MagicMock()
        mock_sampling = MagicMock()

        with patch(
            "util.config.load_basemodel_config_from_file", return_value=mock_basemodel
        ), patch(
            "util.config.load_sampling_config_from_file", return_value=mock_sampling
        ), patch(
            "util.config.validate_cross_config_consistency"
        ) as mock_validate:
            config.load_all_configs(config_paths, validate_consistency=False)

        # Should NOT validate
        mock_validate.assert_not_called()

    def test_load_all_configs_missing_basemodel(self):
        """Test load_all_configs raises ValueError when basemodel config is missing."""
        config_paths = {
            "basemodel": None,
            "sampling": "/path/to/sampling.yaml",
            "calibration": None,
            "output": None,
        }

        with pytest.raises(ValueError, match="Basemodel config is required"):
            config.load_all_configs(config_paths)
