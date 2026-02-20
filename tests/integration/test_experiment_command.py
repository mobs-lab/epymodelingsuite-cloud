"""Integration tests for experiment list command."""

from unittest.mock import Mock, patch

from epycloud.commands import experiment

# Standard test data matching list_experiment_runs return format
RUNS = [
    ("202605/exp1", "20250601-120000-abc12345"),
    ("202605/exp2", "20250602-130000-def67890"),
    ("202605/exp1", "20250603-140000-ghi11111"),
]


def _make_ctx(mock_config, **overrides):
    """Build a ctx dict with sensible defaults for experiment list."""
    args_defaults = {
        "experiment_subcommand": "list",
        "output_format": "table",
        "latest": False,
        "limit": 50,
        "exp_filter": None,
        "bucket": None,
        "dir_prefix": None,
    }
    args_defaults.update(overrides)
    return {
        "config": mock_config,
        "environment": "dev",
        "profile": None,
        "verbose": False,
        "quiet": False,
        "dry_run": False,
        "args": Mock(**args_defaults),
    }


class TestExperimentListCommand:
    """Test experiment list command handler."""

    @patch("epycloud.commands.experiment.handlers.list_experiment_runs", return_value=RUNS)
    @patch("epycloud.commands.experiment.handlers.storage.Client")
    def test_format_uri(self, mock_client, mock_list_runs, mock_config, capsys):
        ctx = _make_ctx(mock_config, output_format="uri")
        assert experiment.handle(ctx) == 0

        lines = capsys.readouterr().out.strip().splitlines()
        assert len(lines) == 3
        for line in lines:
            assert line.startswith("gs://test-bucket/pipeline/test/")
            assert line.endswith("/")

    @patch("epycloud.commands.experiment.handlers.list_experiment_runs", return_value=RUNS)
    @patch("epycloud.commands.experiment.handlers.storage.Client")
    def test_format_args(self, mock_client, mock_list_runs, mock_config, capsys):
        ctx = _make_ctx(mock_config, output_format="args")
        assert experiment.handle(ctx) == 0

        lines = capsys.readouterr().out.strip().splitlines()
        assert len(lines) == 3
        for line in lines:
            assert line.startswith("--exp-id ")
            assert "--run-id " in line

    @patch("epycloud.commands.experiment.handlers.list_experiment_runs", return_value=RUNS)
    @patch("epycloud.commands.experiment.handlers.storage.Client")
    def test_format_table(self, mock_client, mock_list_runs, mock_config, capsys):
        ctx = _make_ctx(mock_config, output_format="table")
        assert experiment.handle(ctx) == 0

        output = capsys.readouterr().out
        assert "202605/exp1" in output
        assert "202605/exp2" in output
        assert "20250601-120000-abc12345" in output

    @patch("epycloud.commands.experiment.handlers.list_experiment_runs", return_value=RUNS)
    @patch("epycloud.commands.experiment.handlers.storage.Client")
    def test_latest_flag(self, mock_client, mock_list_runs, mock_config, capsys):
        ctx = _make_ctx(mock_config, output_format="args", latest=True)
        assert experiment.handle(ctx) == 0

        lines = capsys.readouterr().out.strip().splitlines()
        # Two unique experiments, one run each
        assert len(lines) == 2
        exp_ids = [line.split("--exp-id ")[1].split(" ")[0] for line in lines]
        assert "202605/exp1" in exp_ids
        assert "202605/exp2" in exp_ids
        # exp1 should have the latest run
        for line in lines:
            if "202605/exp1" in line:
                assert "20250603-140000-ghi11111" in line

    @patch("epycloud.commands.experiment.handlers.list_experiment_runs", return_value=RUNS)
    @patch("epycloud.commands.experiment.handlers.storage.Client")
    def test_limit(self, mock_client, mock_list_runs, mock_config, capsys):
        ctx = _make_ctx(mock_config, output_format="args", limit=2)
        assert experiment.handle(ctx) == 0

        lines = capsys.readouterr().out.strip().splitlines()
        assert len(lines) == 2

    @patch("epycloud.commands.experiment.handlers.list_experiment_runs", return_value=RUNS)
    @patch("epycloud.commands.experiment.handlers.storage.Client")
    def test_exp_filter(self, mock_client, mock_list_runs, mock_config, capsys):
        ctx = _make_ctx(mock_config, output_format="args", exp_filter="202605/exp1")
        assert experiment.handle(ctx) == 0

        lines = capsys.readouterr().out.strip().splitlines()
        assert len(lines) == 2
        for line in lines:
            assert "202605/exp1" in line

    @patch(
        "epycloud.commands.experiment.handlers.list_experiment_runs", return_value=[]
    )
    @patch("epycloud.commands.experiment.handlers.storage.Client")
    def test_no_experiments_found(self, mock_client, mock_list_runs, mock_config):
        ctx = _make_ctx(mock_config)
        assert experiment.handle(ctx) == 0

    @patch(
        "epycloud.commands.experiment.handlers.list_experiment_runs",
        side_effect=Exception("GCS error"),
    )
    @patch("epycloud.commands.experiment.handlers.storage.Client")
    def test_gcs_client_failure(self, mock_client, mock_list_runs, mock_config):
        ctx = _make_ctx(mock_config)
        assert experiment.handle(ctx) == 1

    def test_missing_config(self):
        ctx = _make_ctx(None)
        ctx["config"] = None
        assert experiment.handle(ctx) == 2
