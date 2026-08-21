"""Tests for selecting and validating a Cloud Batch data-plane region."""

from unittest.mock import Mock, patch

from epycloud.cli import create_parser
from epycloud.commands.run.validation import validate_cross_region_preflight


def test_workflow_parser_accepts_batch_region():
    """The explicit Batch flag must remain distinct from the workflow region."""
    args = create_parser().parse_args(
        ["run", "workflow", "--exp-id", "test", "--batch-region", "us-east5"]
    )

    assert args.batch_region == "us-east5"


@patch("epycloud.commands.run.validation.subprocess.run")
@patch("epycloud.commands.run.validation.build_cloud.resolve_image_digest")
def test_cross_region_preflight_requires_matching_image_and_subnet(
    mock_digest, mock_run, mock_config
):
    """A replicated digest and a live regional subnet allow submission to proceed."""
    digest = "sha256:" + "a" * 64
    mock_digest.side_effect = [digest, digest]
    mock_run.return_value = Mock(returncode=0, stdout="subnet-link\n", stderr="")

    valid = validate_cross_region_preflight(
        mock_config,
        "test-project",
        "us-central1",
        "us-east5",
        "dev",
        False,
    )

    assert valid is True
    assert mock_digest.call_count == 2
    command = mock_run.call_args.args[0]
    assert "epymodelingsuite-subnet-us-east5" in command
    assert "--region=us-east5" in command


@patch("epycloud.commands.run.validation.subprocess.run")
@patch("epycloud.commands.run.validation.build_cloud.resolve_image_digest")
def test_cross_region_preflight_rejects_a_different_digest(
    mock_digest, mock_run, mock_config, capsys
):
    """A stale destination tag must stop submission and show the repair command."""
    mock_digest.side_effect = ["sha256:" + "a" * 64, "sha256:" + "b" * 64]

    valid = validate_cross_region_preflight(
        mock_config,
        "test-project",
        "us-central1",
        "us-east5",
        "dev",
        False,
    )

    assert valid is False
    mock_run.assert_not_called()
    assert (
        "uv run epycloud build replicate --from us-central1 --to us-east5 --tag dev"
        in capsys.readouterr().out
    )


@patch("epycloud.commands.run.validation.subprocess.run")
@patch("epycloud.commands.run.validation.build_cloud.resolve_image_digest")
def test_cross_region_preflight_rejects_a_missing_subnet(mock_digest, mock_run, mock_config):
    """A matching image alone is insufficient when Batch has no regional subnet."""
    digest = "sha256:" + "a" * 64
    mock_digest.side_effect = [digest, digest]
    mock_run.return_value = Mock(returncode=1, stdout="", stderr="not found")

    valid = validate_cross_region_preflight(
        mock_config,
        "test-project",
        "us-central1",
        "us-east5",
        "dev",
        False,
    )

    assert valid is False
