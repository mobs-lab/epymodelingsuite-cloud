"""Integration tests for input validation."""

from pathlib import Path

import pytest

from epycloud.exceptions import ValidationError
from epycloud.lib.validation import (
    validate_exp_id,
    validate_github_token,
    validate_local_path,
    validate_run_id,
    validate_stage_name,
)


class TestValidateExpId:
    """Test experiment ID validation."""

    def test_valid_exp_id(self):
        """Test valid experiment IDs."""
        assert validate_exp_id("test-sim") == "test-sim"
        assert validate_exp_id("my_experiment_01") == "my_experiment_01"
        assert validate_exp_id("test123") == "test123"
        assert validate_exp_id("  test-sim  ") == "test-sim"  # Trimmed

    def test_invalid_exp_id_empty(self):
        """Test empty experiment ID raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_exp_id("")

        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_exp_id("   ")

    def test_invalid_exp_id_special_chars(self):
        """Test experiment ID with invalid characters."""
        with pytest.raises(ValidationError, match="Must contain only"):
            validate_exp_id("test@exp")

        with pytest.raises(ValidationError, match="Must contain only"):
            validate_exp_id("test exp")  # Space

        # Forward slash is caught by path traversal check first
        with pytest.raises(ValidationError, match="Path traversal"):
            validate_exp_id("test/exp")  # Forward slash

    def test_invalid_exp_id_path_traversal(self):
        """Test path traversal attempts are rejected."""
        with pytest.raises(ValidationError, match="Path traversal not allowed"):
            validate_exp_id("../etc/passwd")

        with pytest.raises(ValidationError, match="Path traversal not allowed"):
            validate_exp_id("test/../exp")

    def test_invalid_exp_id_too_long(self):
        """Test experiment ID length limit."""
        with pytest.raises(ValidationError, match="too long"):
            validate_exp_id("a" * 101)


class TestValidateRunId:
    """Test run ID validation."""

    def test_valid_run_id_workflow_format(self):
        """Test valid workflow-generated run ID."""
        # Format: YYYYMMDD-HHMMSS-xxxxxxxx
        assert validate_run_id("20251107-143052-a1b2c3d4") == "20251107-143052-a1b2c3d4"
        assert validate_run_id("20250101-000000-ffffffff") == "20250101-000000-ffffffff"

    def test_valid_run_id_user_defined(self):
        """Test valid user-defined run ID."""
        assert validate_run_id("my-local-run-01") == "my-local-run-01"
        assert validate_run_id("test_run_123") == "test_run_123"

    def test_invalid_run_id_workflow_format_bad_date(self):
        """Test workflow format with invalid date components."""
        with pytest.raises(ValidationError, match="Invalid month"):
            validate_run_id("20251313-143052-a1b2c3d4")  # Month 13

        with pytest.raises(ValidationError, match="Invalid day"):
            validate_run_id("20251132-143052-a1b2c3d4")  # Day 32

        with pytest.raises(ValidationError, match="Invalid year"):
            validate_run_id("20101107-143052-a1b2c3d4")  # Year 2010

    def test_invalid_run_id_workflow_format_bad_time(self):
        """Test workflow format with invalid time components."""
        with pytest.raises(ValidationError, match="Invalid hour"):
            validate_run_id("20251107-243052-a1b2c3d4")  # Hour 24

        with pytest.raises(ValidationError, match="Invalid minute"):
            validate_run_id("20251107-146052-a1b2c3d4")  # Minute 60

        with pytest.raises(ValidationError, match="Invalid second"):
            validate_run_id("20251107-143060-a1b2c3d4")  # Second 60

    def test_invalid_run_id_wrong_format(self):
        """Test run ID with invalid characters."""
        # "2025-11-07" is actually valid as a user-defined run_id (contains only alphanumeric + dash)
        # Test with actually invalid characters instead
        with pytest.raises(ValidationError, match="Invalid run ID format"):
            validate_run_id("run@id!")  # Special characters

        with pytest.raises(ValidationError, match="Invalid run ID format"):
            validate_run_id("run id")  # Space

    def test_invalid_run_id_empty(self):
        """Test empty run ID raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_run_id("")


class TestValidateLocalPath:
    """Test local path validation."""

    def test_valid_path_exists(self, tmp_path):
        """Test valid existing path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        validated = validate_local_path(test_file, must_exist=True)
        assert validated.exists()
        assert validated.is_absolute()

    def test_valid_path_directory(self, tmp_path):
        """Test valid directory path."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        validated = validate_local_path(test_dir, must_exist=True, must_be_dir=True)
        assert validated.is_dir()

    def test_invalid_path_not_exists(self, tmp_path):
        """Test nonexistent path raises ValidationError."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(ValidationError, match="does not exist"):
            validate_local_path(nonexistent, must_exist=True)

    def test_invalid_path_not_directory(self, tmp_path):
        """Test file path when directory required."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with pytest.raises(ValidationError, match="not a directory"):
            validate_local_path(test_file, must_exist=True, must_be_dir=True)

    def test_path_resolution(self, tmp_path):
        """Test path resolution handles relative paths."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            test_dir = tmp_path / "test_dir"
            test_dir.mkdir()

            # Validate relative path
            validated = validate_local_path(Path("test_dir"), must_exist=True)
            assert validated.is_absolute()
            assert validated == test_dir
        finally:
            os.chdir(original_cwd)


class TestValidateGithubToken:
    """Test GitHub token validation."""

    def test_valid_github_token(self):
        """Test valid GitHub token formats."""
        # Classic tokens
        assert validate_github_token("ghp_1234567890abcdef1234567890abcdef1234")
        assert validate_github_token("gho_1234567890abcdef1234567890abcdef1234")
        assert validate_github_token("ghu_1234567890abcdef1234567890abcdef1234")
        # Fine-grained tokens
        assert validate_github_token("github_pat_11AAAAAA0xxxxxxxxxxxxxxxxx_yyyyyyyyyyyyyyyyyy")

    def test_invalid_github_token_wrong_prefix(self):
        """Test GitHub token with wrong prefix."""
        with pytest.raises(ValidationError, match="Invalid GitHub token format"):
            validate_github_token("invalid_1234567890abcdef1234567890abcdef")

    def test_invalid_github_token_too_short(self):
        """Test GitHub token that's too short."""
        with pytest.raises(ValidationError, match="length unusual"):
            validate_github_token("ghp_short")

    def test_invalid_github_token_empty(self):
        """Test empty GitHub token."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_github_token("")


class TestValidateStageName:
    """Test stage name validation."""

    def test_valid_stage_names(self):
        """Test valid stage names."""
        assert validate_stage_name("builder") == "builder"
        assert validate_stage_name("runner") == "runner"
        assert validate_stage_name("output") == "output"
        assert validate_stage_name("BUILDER") == "builder"  # Normalized to lowercase

    def test_invalid_stage_name(self):
        """Test invalid stage name."""
        with pytest.raises(ValidationError, match="Invalid stage name"):
            validate_stage_name("invalid")

        with pytest.raises(ValidationError, match="Invalid stage name"):
            validate_stage_name("A")  # Legacy names not accepted

    def test_invalid_stage_name_empty(self):
        """Test empty stage name."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_stage_name("")
