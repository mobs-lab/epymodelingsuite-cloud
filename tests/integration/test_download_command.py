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


def _setup_gcs_mock(mock_storage_client, prefix_map, run_map=None, blob_map=None):
    """Set up a GCS client mock with recursive experiment listing.

    Parameters
    ----------
    prefix_map : dict[str, list[str]]
        Prefix -> child prefixes. Maps each GCS prefix to its direct
        children. Used by list_experiments (recursive scanning) and
        list_run_ids.
    run_map : dict[str, list[str]]
        Experiment prefix -> run prefixes (convenience, merged into prefix_map)
    blob_map : dict[str, list[Mock]]
        Output prefix -> list of mock blobs
    """
    mock_client = Mock()
    mock_storage_client.return_value = mock_client
    mock_bucket = Mock()
    mock_client.bucket.return_value = mock_bucket

    blob_map = blob_map or {}
    # Merge run_map into prefix_map for unified lookup
    all_prefixes = dict(prefix_map)
    if run_map:
        all_prefixes.update(run_map)

    def list_blobs_side_effect(prefix, delimiter=None):  # noqa: ARG001
        # Check blob_map first (outputs/ listings return plain iterables)
        if prefix in blob_map:
            return blob_map[prefix]
        # Check for outputs prefix pattern
        if "outputs/" in prefix:
            return []
        # Unified prefix lookup
        if prefix in all_prefixes:
            return _make_blob_iterator(prefixes=all_prefixes[prefix])
        return _make_blob_iterator()

    mock_bucket.list_blobs.side_effect = list_blobs_side_effect

    return mock_client, mock_bucket


# Helper: standard two-level prefix_map for pipeline/test/202605/exp1
def _standard_prefix_map(exp_names=None, run_id="20250101-120000-abc12345"):
    """Build a standard two-level prefix_map for tests.

    Returns prefix_map and run_map for the standard layout:
    pipeline/test/202605/{exp_name}/{run_id}/
    """
    exp_names = exp_names or ["exp1"]
    prefix_map = {
        "pipeline/test/": ["pipeline/test/202605/"],
        "pipeline/test/202605/": [
            f"pipeline/test/202605/{name}/" for name in exp_names
        ],
    }
    run_map = {}
    for name in exp_names:
        exp_prefix = f"pipeline/test/202605/{name}/"
        prefix_map[exp_prefix] = [f"{exp_prefix}{run_id}/"]
        run_map[exp_prefix] = [f"{exp_prefix}{run_id}/"]
    return prefix_map, run_map


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
        prefix_map, _ = _standard_prefix_map()
        _setup_gcs_mock(
            mock_storage_client,
            prefix_map=prefix_map,
        )
        ctx = _make_ctx(mock_config, tmp_path, exp_filter="202699/*")
        assert download.handle(ctx) == 0

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_successful_download(self, mock_storage_client, mock_config, tmp_path):
        blob1 = Mock()
        blob1.name = "pipeline/test/202605/exp1/20250101-120000-abc12345/outputs/ts/posterior_grid.pdf"
        blob2 = Mock()
        blob2.name = "pipeline/test/202605/exp1/20250101-120000-abc12345/outputs/ts/quantiles_grid_sidebyside.pdf"

        prefix_map, run_map = _standard_prefix_map()
        _setup_gcs_mock(
            mock_storage_client,
            prefix_map=prefix_map,
            run_map=run_map,
            blob_map={
                "pipeline/test/202605/exp1/20250101-120000-abc12345/outputs/": [
                    blob1,
                    blob2,
                ]
            },
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

        prefix_map, run_map = _standard_prefix_map()
        _setup_gcs_mock(
            mock_storage_client,
            prefix_map=prefix_map,
            run_map=run_map,
        )

        ctx = _make_ctx(mock_config, tmp_path, yes=False)
        assert download.handle(ctx) == 0
        assert mock_confirm.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_yes_flag_skips_confirmation(self, mock_storage_client, mock_config, tmp_path):
        prefix_map, run_map = _standard_prefix_map()
        _setup_gcs_mock(
            mock_storage_client,
            prefix_map=prefix_map,
            run_map=run_map,
        )

        with patch("epycloud.commands.download.handlers.ask_confirmation") as mock_confirm:
            ctx = _make_ctx(mock_config, tmp_path, yes=True)
            download.handle(ctx)
            assert not mock_confirm.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_multi_run_selects_latest(self, mock_storage_client, mock_config, tmp_path):
        blob = Mock()
        blob.name = "pipeline/test/202605/exp1/20250103-140000-ccc78901/outputs/ts/posterior_grid.pdf"

        _setup_gcs_mock(
            mock_storage_client,
            prefix_map={
                "pipeline/test/": ["pipeline/test/202605/"],
                "pipeline/test/202605/": ["pipeline/test/202605/exp1/"],
                "pipeline/test/202605/exp1/": [
                    "pipeline/test/202605/exp1/20250101-120000-aaa12345/",
                    "pipeline/test/202605/exp1/20250102-130000-bbb45678/",
                    "pipeline/test/202605/exp1/20250103-140000-ccc78901/",
                ],
            },
            run_map={
                "pipeline/test/202605/exp1/": [
                    "pipeline/test/202605/exp1/20250101-120000-aaa12345/",
                    "pipeline/test/202605/exp1/20250102-130000-bbb45678/",
                    "pipeline/test/202605/exp1/20250103-140000-ccc78901/",
                ]
            },
            blob_map={
                "pipeline/test/202605/exp1/20250103-140000-ccc78901/outputs/": [blob]
            },
        )

        ctx = _make_ctx(mock_config, tmp_path)
        assert download.handle(ctx) == 0
        assert blob.download_to_filename.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_skip_existing_files(self, mock_storage_client, mock_config, tmp_path):
        blob = Mock()
        blob.name = "pipeline/test/202605/exp1/20250101-120000-abc12345/outputs/ts/posterior_grid.pdf"

        prefix_map, run_map = _standard_prefix_map()
        _setup_gcs_mock(
            mock_storage_client,
            prefix_map=prefix_map,
            run_map=run_map,
            blob_map={
                "pipeline/test/202605/exp1/20250101-120000-abc12345/outputs/": [blob]
            },
        )

        # Pre-create the file (now uses full exp_path_rel: 202605/exp1)
        out = tmp_path / "downloads" / "202605" / "exp1"
        out.mkdir(parents=True)
        (out / "posterior_grid.pdf").touch()

        ctx = _make_ctx(mock_config, tmp_path)
        assert download.handle(ctx) == 0
        assert not blob.download_to_filename.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_bucket_override(self, mock_storage_client, mock_config, tmp_path):
        mock_client, _ = _setup_gcs_mock(
            mock_storage_client,
            prefix_map={},
        )

        ctx = _make_ctx(mock_config, tmp_path, exp_filter="*", bucket="my-bucket")
        download.handle(ctx)
        mock_client.bucket.assert_called_with("my-bucket")

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_dir_prefix_override(self, mock_storage_client, mock_config, tmp_path):
        _, mock_bucket = _setup_gcs_mock(
            mock_storage_client,
            prefix_map={},
        )

        ctx = _make_ctx(mock_config, tmp_path, exp_filter="*", dir_prefix="custom/pfx")
        download.handle(ctx)
        first_call = mock_bucket.list_blobs.call_args_list[0]
        assert first_call[1]["prefix"] == "custom/pfx/"

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_pattern_auto_appends_wildcard(self, mock_storage_client, mock_config, tmp_path):
        prefix_map, run_map = _standard_prefix_map(["exp1", "exp2"])
        _setup_gcs_mock(
            mock_storage_client,
            prefix_map=prefix_map,
            run_map=run_map,
        )

        # Pattern "202605/" should match both experiments
        ctx = _make_ctx(mock_config, tmp_path, exp_filter="202605/")
        assert download.handle(ctx) == 0

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_hosp_experiment_gets_extra_file(
        self, mock_storage_client, mock_config, tmp_path
    ):
        run_id = "20250101-120000-abc12345"
        blob1 = Mock()
        blob1.name = f"pipeline/test/202605/hosp_x/{run_id}/outputs/ts/posterior_grid.pdf"
        blob2 = Mock()
        blob2.name = f"pipeline/test/202605/hosp_x/{run_id}/outputs/ts/quantiles_grid_sidebyside.pdf"
        blob3 = Mock()
        blob3.name = f"pipeline/test/202605/hosp_x/{run_id}/outputs/ts/categorical_rate_trends.pdf"

        prefix_map, run_map = _standard_prefix_map(["hosp_x"])
        _setup_gcs_mock(
            mock_storage_client,
            prefix_map=prefix_map,
            run_map=run_map,
            blob_map={
                f"pipeline/test/202605/hosp_x/{run_id}/outputs/": [blob1, blob2, blob3]
            },
        )

        ctx = _make_ctx(mock_config, tmp_path, exp_filter="202605/hosp_*")
        assert download.handle(ctx) == 0
        assert blob1.download_to_filename.called
        assert blob2.download_to_filename.called
        assert blob3.download_to_filename.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_exact_pattern_matches_sub_experiments(
        self, mock_storage_client, mock_config, tmp_path
    ):
        """Exact pattern without trailing slash matches sub-experiments."""
        run_id = "20250101-120000-abc12345"
        blob1 = Mock()
        blob1.name = f"pipeline/test/test/reff_resimm_beta/exp1/{run_id}/outputs/ts/posterior_grid.pdf"
        blob2 = Mock()
        blob2.name = f"pipeline/test/test/reff_resimm_beta/exp2/{run_id}/outputs/ts/posterior_grid.pdf"

        _setup_gcs_mock(
            mock_storage_client,
            prefix_map={
                "pipeline/test/test/reff_resimm_beta/": [
                    "pipeline/test/test/reff_resimm_beta/exp1/",
                    "pipeline/test/test/reff_resimm_beta/exp2/",
                ],
                "pipeline/test/test/reff_resimm_beta/exp1/": [
                    f"pipeline/test/test/reff_resimm_beta/exp1/{run_id}/"
                ],
                "pipeline/test/test/reff_resimm_beta/exp2/": [
                    f"pipeline/test/test/reff_resimm_beta/exp2/{run_id}/"
                ],
            },
            run_map={
                "pipeline/test/test/reff_resimm_beta/exp1/": [
                    f"pipeline/test/test/reff_resimm_beta/exp1/{run_id}/"
                ],
                "pipeline/test/test/reff_resimm_beta/exp2/": [
                    f"pipeline/test/test/reff_resimm_beta/exp2/{run_id}/"
                ],
            },
            blob_map={
                f"pipeline/test/test/reff_resimm_beta/exp1/{run_id}/outputs/": [blob1],
                f"pipeline/test/test/reff_resimm_beta/exp2/{run_id}/outputs/": [blob2],
            },
        )

        # No trailing slash, no wildcards - should still match sub-experiments
        ctx = _make_ctx(mock_config, tmp_path, exp_filter="test/reff_resimm_beta")
        assert download.handle(ctx) == 0
        assert blob1.download_to_filename.called
        assert blob2.download_to_filename.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_exact_pattern_matches_direct_experiment(
        self, mock_storage_client, mock_config, tmp_path
    ):
        """Exact pattern without trailing slash matches a direct experiment."""
        run_id = "20250101-120000-abc12345"
        blob = Mock()
        blob.name = f"pipeline/test/testdir/myexp01/{run_id}/outputs/ts/posterior_grid.pdf"

        _setup_gcs_mock(
            mock_storage_client,
            prefix_map={
                "pipeline/test/testdir/myexp01/": [
                    f"pipeline/test/testdir/myexp01/{run_id}/"
                ],
            },
            run_map={
                "pipeline/test/testdir/myexp01/": [
                    f"pipeline/test/testdir/myexp01/{run_id}/"
                ],
            },
            blob_map={
                f"pipeline/test/testdir/myexp01/{run_id}/outputs/": [blob]
            },
        )

        # No trailing slash - should match the exact experiment
        ctx = _make_ctx(mock_config, tmp_path, exp_filter="testdir/myexp01")
        assert download.handle(ctx) == 0
        assert blob.download_to_filename.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_nested_exp_id_with_trailing_slash(
        self, mock_storage_client, mock_config, tmp_path
    ):
        """Trailing slash on nested exp_id matches the experiment."""
        run_id = "20250101-120000-abc12345"
        blob = Mock()
        blob.name = f"pipeline/test/testdir/myexp01/{run_id}/outputs/ts/posterior_grid.pdf"

        _setup_gcs_mock(
            mock_storage_client,
            prefix_map={
                "pipeline/test/": ["pipeline/test/testdir/"],
                "pipeline/test/testdir/": ["pipeline/test/testdir/myexp01/"],
                "pipeline/test/testdir/myexp01/": [
                    f"pipeline/test/testdir/myexp01/{run_id}/"
                ],
            },
            run_map={
                "pipeline/test/testdir/myexp01/": [
                    f"pipeline/test/testdir/myexp01/{run_id}/"
                ],
            },
            blob_map={
                f"pipeline/test/testdir/myexp01/{run_id}/outputs/": [blob]
            },
        )

        ctx = _make_ctx(mock_config, tmp_path, exp_filter="testdir/myexp01/")
        assert download.handle(ctx) == 0
        assert blob.download_to_filename.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_three_level_nested_experiments(
        self, mock_storage_client, mock_config, tmp_path
    ):
        """Three-level nested experiments discovered and downloaded."""
        run_id = "20250101-120000-abc12345"
        blob1 = Mock()
        blob1.name = f"pipeline/test/test/myexperiments/exp1/{run_id}/outputs/ts/posterior_grid.pdf"
        blob2 = Mock()
        blob2.name = f"pipeline/test/test/myexperiments/exp2/{run_id}/outputs/ts/posterior_grid.pdf"

        _setup_gcs_mock(
            mock_storage_client,
            prefix_map={
                "pipeline/test/": ["pipeline/test/test/"],
                "pipeline/test/test/": ["pipeline/test/test/myexperiments/"],
                "pipeline/test/test/myexperiments/": [
                    "pipeline/test/test/myexperiments/exp1/",
                    "pipeline/test/test/myexperiments/exp2/",
                ],
                "pipeline/test/test/myexperiments/exp1/": [
                    f"pipeline/test/test/myexperiments/exp1/{run_id}/"
                ],
                "pipeline/test/test/myexperiments/exp2/": [
                    f"pipeline/test/test/myexperiments/exp2/{run_id}/"
                ],
            },
            run_map={
                "pipeline/test/test/myexperiments/exp1/": [
                    f"pipeline/test/test/myexperiments/exp1/{run_id}/"
                ],
                "pipeline/test/test/myexperiments/exp2/": [
                    f"pipeline/test/test/myexperiments/exp2/{run_id}/"
                ],
            },
            blob_map={
                f"pipeline/test/test/myexperiments/exp1/{run_id}/outputs/": [blob1],
                f"pipeline/test/test/myexperiments/exp2/{run_id}/outputs/": [blob2],
            },
        )

        ctx = _make_ctx(mock_config, tmp_path, exp_filter="test/myexperiments/*")
        assert download.handle(ctx) == 0
        assert blob1.download_to_filename.called
        assert blob2.download_to_filename.called

    @patch("epycloud.commands.download.handlers.storage.Client")
    def test_local_directory_preserves_hierarchy(
        self, mock_storage_client, mock_config, tmp_path
    ):
        """Local download directory uses full exp_path_rel, not just exp_name."""
        run_id = "20250101-120000-abc12345"
        blob = Mock()
        blob.name = f"pipeline/test/testdir/myexp01/{run_id}/outputs/ts/posterior_grid.pdf"

        _setup_gcs_mock(
            mock_storage_client,
            prefix_map={
                "pipeline/test/": ["pipeline/test/testdir/"],
                "pipeline/test/testdir/": ["pipeline/test/testdir/myexp01/"],
                "pipeline/test/testdir/myexp01/": [
                    f"pipeline/test/testdir/myexp01/{run_id}/"
                ],
            },
            run_map={
                "pipeline/test/testdir/myexp01/": [
                    f"pipeline/test/testdir/myexp01/{run_id}/"
                ],
            },
            blob_map={
                f"pipeline/test/testdir/myexp01/{run_id}/outputs/": [blob]
            },
        )

        ctx = _make_ctx(mock_config, tmp_path, exp_filter="testdir/myexp01/")
        assert download.handle(ctx) == 0

        # File should be at downloads/testdir/myexp01/, not downloads/myexp01/
        expected_dir = tmp_path / "downloads" / "testdir" / "myexp01"
        assert expected_dir.exists()
        # And NOT at the flat path
        flat_dir = tmp_path / "downloads" / "myexp01"
        assert not flat_dir.exists()
