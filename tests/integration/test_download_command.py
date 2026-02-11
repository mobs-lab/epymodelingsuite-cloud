"""Integration tests for download command."""

from unittest.mock import Mock, patch

from epycloud.commands import download


def _make_blob_iterator(prefixes=None):
    """Create a mock that behaves like GCS list_blobs result."""
    mock = Mock()
    mock.__iter__ = Mock(return_value=iter([]))
    mock.prefixes = prefixes or []
    return mock


def _make_ctx(mock_config, tmp_path, **overrides):
    """Build a ctx dict with sensible defaults."""
    args_defaults = {
        "exp_filter": "202605/*",
        "output_dir": str(tmp_path / "downloads"),
        "name_format": "short",
        "nest_runs": False,
        "bucket": None,
        "dir_prefix": None,
        "yes": True,
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


def _setup_gcs_mock(mock_storage_client, week_prefixes, exp_map, run_map, blob_map=None):
    """Set up a GCS client mock with two-level experiment listing.

    Parameters
    ----------
    week_prefixes : list[str]
        Week-level prefixes (e.g. ["pipeline/test/202605/"])
    exp_map : dict[str, list[str]]
        Week prefix -> experiment prefixes
    run_map : dict[str, list[str]]
        Experiment prefix -> run prefixes
    blob_map : dict[str, list[Mock]]
        Output prefix -> list of mock blobs
    """
    mock_client = Mock()
    mock_storage_client.return_value = mock_client
    mock_bucket = Mock()
    mock_client.bucket.return_value = mock_bucket

    blob_map = blob_map or {}

    def list_blobs_side_effect(prefix, delimiter=None):  # noqa: ARG001
        # Check blob_map first (outputs/ listings return plain iterables)
        if prefix in blob_map:
            return blob_map[prefix]
        # Check for outputs prefix pattern
        if "outputs/" in prefix:
            return []
        # Delimiter-based directory listing
        if prefix in exp_map:
            return _make_blob_iterator(prefixes=exp_map[prefix])
        if prefix in run_map:
            return _make_blob_iterator(prefixes=run_map[prefix])
        # Top-level: week listing
        for wp in week_prefixes:
            if prefix == wp.rsplit("/", 2)[0] + "/" or prefix in [
                p.rsplit("/", 2)[0] + "/" for p in week_prefixes
            ]:
                return _make_blob_iterator(prefixes=week_prefixes)
        return _make_blob_iterator()

    mock_bucket.list_blobs.side_effect = list_blobs_side_effect

    return mock_client, mock_bucket


class TestDownloadCommand:
    """Test download command main handler."""

    def test_missing_config(self, tmp_path):
        ctx = _make_ctx(None, tmp_path)
        ctx["config"] = None
        assert download.handle(ctx) == 2

    def test_missing_bucket_name(self, tmp_path):
        config = {
            "google_cloud": {"project_id": "test", "region": "us-central1"},
            "storage": {},
        }
        ctx = _make_ctx(config, tmp_path)
        assert download.handle(ctx) == 2

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_gcs_client_failure(self, mock_storage_client, mock_config, tmp_path):
        mock_storage_client.side_effect = Exception("auth fail")
        ctx = _make_ctx(mock_config, tmp_path)
        assert download.handle(ctx) == 1

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_list_experiments_failure(self, mock_storage_client, mock_config, tmp_path):
        mock_client = Mock()
        mock_storage_client.return_value = mock_client
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.list_blobs.side_effect = Exception("GCS error")

        ctx = _make_ctx(mock_config, tmp_path)
        assert download.handle(ctx) == 1

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_no_experiments_found(self, mock_storage_client, mock_config, tmp_path):
        mock_client = Mock()
        mock_storage_client.return_value = mock_client
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.list_blobs.return_value = _make_blob_iterator()

        ctx = _make_ctx(mock_config, tmp_path, exp_filter="*")
        assert download.handle(ctx) == 0

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_no_pattern_matches(self, mock_storage_client, mock_config, tmp_path):
        _setup_gcs_mock(
            mock_storage_client,
            week_prefixes=["pipeline/test/202605/"],
            exp_map={"pipeline/test/202605/": ["pipeline/test/202605/exp1/"]},
            run_map={},
        )
        ctx = _make_ctx(mock_config, tmp_path, exp_filter="202699/*")
        assert download.handle(ctx) == 0

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_successful_download(self, mock_storage_client, mock_config, tmp_path):
        blob1 = Mock()
        blob1.name = "pipeline/test/202605/exp1/run1/outputs/ts/posterior_grid.pdf"
        blob2 = Mock()
        blob2.name = "pipeline/test/202605/exp1/run1/outputs/ts/quantiles_grid_sidebyside.pdf"

        _setup_gcs_mock(
            mock_storage_client,
            week_prefixes=["pipeline/test/202605/"],
            exp_map={"pipeline/test/202605/": ["pipeline/test/202605/exp1/"]},
            run_map={"pipeline/test/202605/exp1/": ["pipeline/test/202605/exp1/run1/"]},
            blob_map={"pipeline/test/202605/exp1/run1/outputs/": [blob1, blob2]},
        )

        ctx = _make_ctx(mock_config, tmp_path)
        assert download.handle(ctx) == 0
        assert blob1.download_to_filename.called
        assert blob2.download_to_filename.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    @patch("epycloud.commands.download.handlers.ask_confirmation")
    def test_cancelled_by_user(
        self, mock_confirm, mock_storage_client, mock_config, tmp_path
    ):
        mock_confirm.return_value = False

        _setup_gcs_mock(
            mock_storage_client,
            week_prefixes=["pipeline/test/202605/"],
            exp_map={"pipeline/test/202605/": ["pipeline/test/202605/exp1/"]},
            run_map={"pipeline/test/202605/exp1/": ["pipeline/test/202605/exp1/run1/"]},
        )

        ctx = _make_ctx(mock_config, tmp_path, yes=False)
        assert download.handle(ctx) == 0
        assert mock_confirm.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_yes_flag_skips_confirmation(self, mock_storage_client, mock_config, tmp_path):
        _setup_gcs_mock(
            mock_storage_client,
            week_prefixes=["pipeline/test/202605/"],
            exp_map={"pipeline/test/202605/": ["pipeline/test/202605/exp1/"]},
            run_map={"pipeline/test/202605/exp1/": ["pipeline/test/202605/exp1/run1/"]},
        )

        with patch("epycloud.commands.download.handlers.ask_confirmation") as mock_confirm:
            ctx = _make_ctx(mock_config, tmp_path, yes=True)
            download.handle(ctx)
            assert not mock_confirm.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_multi_run_selects_latest(self, mock_storage_client, mock_config, tmp_path):
        blob = Mock()
        blob.name = "pipeline/test/202605/exp1/run3/outputs/ts/posterior_grid.pdf"

        _setup_gcs_mock(
            mock_storage_client,
            week_prefixes=["pipeline/test/202605/"],
            exp_map={"pipeline/test/202605/": ["pipeline/test/202605/exp1/"]},
            run_map={
                "pipeline/test/202605/exp1/": [
                    "pipeline/test/202605/exp1/20250101-aaa/",
                    "pipeline/test/202605/exp1/20250102-bbb/",
                    "pipeline/test/202605/exp1/20250103-ccc/",
                ]
            },
            # Only the latest run has blobs
            blob_map={"pipeline/test/202605/exp1/20250103-ccc/outputs/": [blob]},
        )

        ctx = _make_ctx(mock_config, tmp_path)
        assert download.handle(ctx) == 0
        assert blob.download_to_filename.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_skip_existing_files(self, mock_storage_client, mock_config, tmp_path):
        blob = Mock()
        blob.name = "pipeline/test/202605/exp1/run1/outputs/ts/posterior_grid.pdf"

        _setup_gcs_mock(
            mock_storage_client,
            week_prefixes=["pipeline/test/202605/"],
            exp_map={"pipeline/test/202605/": ["pipeline/test/202605/exp1/"]},
            run_map={"pipeline/test/202605/exp1/": ["pipeline/test/202605/exp1/run1/"]},
            blob_map={"pipeline/test/202605/exp1/run1/outputs/": [blob]},
        )

        # Pre-create the file
        out = tmp_path / "downloads" / "exp1"
        out.mkdir(parents=True)
        (out / "posterior_grid.pdf").touch()

        ctx = _make_ctx(mock_config, tmp_path)
        assert download.handle(ctx) == 0
        assert not blob.download_to_filename.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_bucket_override(self, mock_storage_client, mock_config, tmp_path):
        mock_client, _ = _setup_gcs_mock(
            mock_storage_client,
            week_prefixes=[],
            exp_map={},
            run_map={},
        )

        ctx = _make_ctx(mock_config, tmp_path, exp_filter="*", bucket="my-bucket")
        download.handle(ctx)
        mock_client.bucket.assert_called_with("my-bucket")

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_dir_prefix_override(self, mock_storage_client, mock_config, tmp_path):
        _, mock_bucket = _setup_gcs_mock(
            mock_storage_client,
            week_prefixes=[],
            exp_map={},
            run_map={},
        )

        ctx = _make_ctx(mock_config, tmp_path, exp_filter="*", dir_prefix="custom/pfx")
        download.handle(ctx)
        first_call = mock_bucket.list_blobs.call_args_list[0]
        assert first_call[1]["prefix"] == "custom/pfx/"

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_pattern_auto_appends_wildcard(self, mock_storage_client, mock_config, tmp_path):
        _setup_gcs_mock(
            mock_storage_client,
            week_prefixes=["pipeline/test/202605/"],
            exp_map={
                "pipeline/test/202605/": [
                    "pipeline/test/202605/exp1/",
                    "pipeline/test/202605/exp2/",
                ]
            },
            run_map={
                "pipeline/test/202605/exp1/": ["pipeline/test/202605/exp1/run1/"],
                "pipeline/test/202605/exp2/": ["pipeline/test/202605/exp2/run1/"],
            },
        )

        # Pattern "202605/" should auto-append "*" and match both experiments
        ctx = _make_ctx(mock_config, tmp_path, exp_filter="202605/")
        assert download.handle(ctx) == 0

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_hosp_experiment_gets_extra_file(
        self, mock_storage_client, mock_config, tmp_path
    ):
        blob1 = Mock()
        blob1.name = "pipeline/test/202605/hosp_x/run1/outputs/ts/posterior_grid.pdf"
        blob2 = Mock()
        blob2.name = (
            "pipeline/test/202605/hosp_x/run1/outputs/ts/quantiles_grid_sidebyside.pdf"
        )
        blob3 = Mock()
        blob3.name = (
            "pipeline/test/202605/hosp_x/run1/outputs/ts/categorical_rate_trends.pdf"
        )

        _setup_gcs_mock(
            mock_storage_client,
            week_prefixes=["pipeline/test/202605/"],
            exp_map={"pipeline/test/202605/": ["pipeline/test/202605/hosp_x/"]},
            run_map={
                "pipeline/test/202605/hosp_x/": [
                    "pipeline/test/202605/hosp_x/run1/"
                ]
            },
            blob_map={
                "pipeline/test/202605/hosp_x/run1/outputs/": [blob1, blob2, blob3]
            },
        )

        ctx = _make_ctx(mock_config, tmp_path, exp_filter="202605/hosp_*")
        assert download.handle(ctx) == 0
        assert blob1.download_to_filename.called
        assert blob2.download_to_filename.called
        assert blob3.download_to_filename.called
