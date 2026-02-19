"""Unit tests for download operations."""

from unittest.mock import Mock

from epycloud.commands.download.operations import (
    build_local_filename,
    filter_experiments,
    find_matching_blobs,
    get_target_files,
    list_experiments,
    list_run_ids,
)
from epycloud.lib.gcs import extract_scan_prefix


def _make_blob_iterator(prefixes=None):
    """Create a mock that behaves like GCS list_blobs result.

    The real API returns an iterator you consume, then access .prefixes.
    """
    mock = Mock()
    mock.__iter__ = Mock(return_value=iter([]))
    mock.prefixes = prefixes or []
    return mock


class TestGetTargetFiles:
    """Test get_target_files function."""

    def test_hosp_prefix_gets_three_files(self):
        result = get_target_files("202605/hosp_smc_rmse_202552-202605")
        assert len(result) == 3
        assert "posterior_grid.pdf" in result
        assert "quantiles_grid_sidebyside.pdf" in result
        assert "categorical_rate_trends.pdf" in result

    def test_hosp_prefix_without_week(self):
        result = get_target_files("hosp_smc_rmse_202552-202605")
        assert len(result) == 3

    def test_ed_prefix_gets_two_files(self):
        result = get_target_files("202605/ed_smc_rmse_202552-202605")
        assert len(result) == 2
        assert "categorical_rate_trends.pdf" not in result

    def test_metro_prefix_gets_two_files(self):
        result = get_target_files("202605/metro_smc_rmse_202552-202605")
        assert len(result) == 2


class TestFilterExperiments:
    """Test filter_experiments function."""

    def test_week_wildcard(self):
        experiments = ["202605/exp1", "202605/exp2", "202606/exp3"]
        result = filter_experiments(experiments, "202605/*")
        assert result == ["202605/exp1", "202605/exp2"]

    def test_prefix_pattern(self):
        experiments = ["202605/hosp_a", "202605/hosp_b", "202605/ed_a"]
        result = filter_experiments(experiments, "202605/hosp_*")
        assert len(result) == 2

    def test_no_match(self):
        result = filter_experiments(["202605/exp1"], "202606/*")
        assert result == []

    def test_cross_week_pattern(self):
        experiments = ["202605/ed_a", "202606/ed_b", "202606/hosp_a"]
        result = filter_experiments(experiments, "*/ed_*")
        assert result == ["202605/ed_a", "202606/ed_b"]

    def test_list_of_patterns(self):
        experiments = ["202605/exp1", "202605/exp2", "202606/exp3"]
        result = filter_experiments(experiments, ["202605/*", "202606/*"])
        assert result == ["202605/exp1", "202605/exp2", "202606/exp3"]

    def test_trailing_slash_exact_experiment(self):
        """A list with both wildcard and exact match handles trailing slash cases."""
        experiments = ["testdir/myexp01", "testdir/myexp02"]
        result = filter_experiments(experiments, ["testdir/myexp01/*", "testdir/myexp01"])
        assert result == ["testdir/myexp01"]

    def test_single_string_backward_compat(self):
        experiments = ["202605/exp1", "202605/exp2"]
        result = filter_experiments(experiments, "202605/*")
        assert result == ["202605/exp1", "202605/exp2"]


class TestBuildLocalFilename:
    """Test build_local_filename function."""

    def test_short_names(self):
        blob = Mock()
        blob.name = "pipeline/flu/202605/exp1/run1/outputs/ts/posterior_grid.pdf"
        assert build_local_filename(blob, long_names=False) == "posterior_grid.pdf"

    def test_long_names_strips_prefix(self):
        blob = Mock()
        blob.name = "pipeline/flu/202605/exp1/run1/outputs/ts/posterior_grid.pdf"
        result = build_local_filename(blob, long_names=True, dir_prefix="pipeline/flu/")
        assert result == "202605_exp1_run1_outputs_ts_posterior_grid.pdf"
        assert not result.startswith("pipeline_flu_")

    def test_long_names_no_prefix(self):
        blob = Mock()
        blob.name = "202605/exp1/run1/outputs/file.pdf"
        result = build_local_filename(blob, long_names=True)
        assert result == "202605_exp1_run1_outputs_file.pdf"

    def test_long_names_prefix_not_matching(self):
        blob = Mock()
        blob.name = "other/path/file.pdf"
        result = build_local_filename(blob, long_names=True, dir_prefix="pipeline/flu/")
        assert result == "other_path_file.pdf"

    def test_empty_blob_name(self):
        blob = Mock()
        blob.name = None
        result = build_local_filename(blob, long_names=False)
        assert result == ""


class TestListExperiments:
    """Test list_experiments function."""

    def test_two_level_standard_structure(self):
        """Standard week/exp structure with run_id children."""
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket

        def list_blobs_side_effect(prefix, delimiter="/"):
            if prefix == "pipeline/flu/":
                return _make_blob_iterator(
                    prefixes=["pipeline/flu/202605/", "pipeline/flu/202606/"]
                )
            elif prefix == "pipeline/flu/202605/":
                return _make_blob_iterator(
                    prefixes=["pipeline/flu/202605/exp_a/", "pipeline/flu/202605/exp_b/"]
                )
            elif prefix == "pipeline/flu/202605/exp_a/":
                return _make_blob_iterator(
                    prefixes=["pipeline/flu/202605/exp_a/20250101-120000-abc12345/"]
                )
            elif prefix == "pipeline/flu/202605/exp_b/":
                return _make_blob_iterator(
                    prefixes=["pipeline/flu/202605/exp_b/20250102-130000-def45678/"]
                )
            elif prefix == "pipeline/flu/202606/":
                return _make_blob_iterator(
                    prefixes=["pipeline/flu/202606/exp_c/"]
                )
            elif prefix == "pipeline/flu/202606/exp_c/":
                return _make_blob_iterator(
                    prefixes=["pipeline/flu/202606/exp_c/20250103-140000-aabb7890/"]
                )
            return _make_blob_iterator()

        mock_bucket.list_blobs.side_effect = list_blobs_side_effect

        result = list_experiments(mock_client, "test-bucket", "pipeline/flu/")
        assert result == ["202605/exp_a", "202605/exp_b", "202606/exp_c"]

    def test_three_level_nested_experiments(self):
        """Nested experiments like test/myexperiments/exp1."""
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket

        def list_blobs_side_effect(prefix, delimiter="/"):
            if prefix == "pipeline/flu/":
                return _make_blob_iterator(
                    prefixes=["pipeline/flu/test/"]
                )
            elif prefix == "pipeline/flu/test/":
                return _make_blob_iterator(
                    prefixes=["pipeline/flu/test/myexperiments/"]
                )
            elif prefix == "pipeline/flu/test/myexperiments/":
                return _make_blob_iterator(
                    prefixes=[
                        "pipeline/flu/test/myexperiments/exp1/",
                        "pipeline/flu/test/myexperiments/exp2/",
                    ]
                )
            elif prefix == "pipeline/flu/test/myexperiments/exp1/":
                return _make_blob_iterator(
                    prefixes=["pipeline/flu/test/myexperiments/exp1/20250101-120000-abc12345/"]
                )
            elif prefix == "pipeline/flu/test/myexperiments/exp2/":
                return _make_blob_iterator(
                    prefixes=["pipeline/flu/test/myexperiments/exp2/20250102-130000-def45678/"]
                )
            return _make_blob_iterator()

        mock_bucket.list_blobs.side_effect = list_blobs_side_effect

        result = list_experiments(mock_client, "test-bucket", "pipeline/flu/")
        assert result == ["test/myexperiments/exp1", "test/myexperiments/exp2"]

    def test_no_children(self):
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.list_blobs.return_value = _make_blob_iterator()

        result = list_experiments(mock_client, "test-bucket", "pipeline/flu/")
        assert result == []

    def test_directory_with_no_run_ids(self):
        """Directory with children that don't match run_id pattern recurses."""
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket

        def list_blobs_side_effect(prefix, delimiter="/"):
            if prefix == "pipeline/flu/":
                return _make_blob_iterator(prefixes=["pipeline/flu/202605/"])
            elif prefix == "pipeline/flu/202605/":
                # No children at all
                return _make_blob_iterator()
            return _make_blob_iterator()

        mock_bucket.list_blobs.side_effect = list_blobs_side_effect

        result = list_experiments(mock_client, "test-bucket", "pipeline/flu/")
        assert result == []


class TestListRunIds:
    """Test list_run_ids function."""

    def test_multiple_runs(self):
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.list_blobs.return_value = _make_blob_iterator(
            prefixes=[
                "pipeline/flu/202605/exp1/20250101-120000-abc123/",
                "pipeline/flu/202605/exp1/20250103-140000-ghi789/",
                "pipeline/flu/202605/exp1/20250102-130000-def456/",
            ]
        )

        result = list_run_ids(mock_client, "test-bucket", "pipeline/flu/202605/exp1")

        assert len(result) == 3
        assert result == sorted(result)

    def test_no_runs(self):
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.list_blobs.return_value = _make_blob_iterator()

        result = list_run_ids(mock_client, "test-bucket", "pipeline/flu/202605/exp1")
        assert result == []

    def test_trailing_slash_on_exp_path(self):
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.list_blobs.return_value = _make_blob_iterator(
            prefixes=["pipeline/flu/202605/exp1/run1/"]
        )

        result = list_run_ids(mock_client, "test-bucket", "pipeline/flu/202605/exp1/")
        assert result == ["run1"]


class TestFindMatchingBlobs:
    """Test find_matching_blobs function."""

    def test_filters_by_target_filenames(self):
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket

        blob_match = Mock()
        blob_match.name = "path/outputs/ts/posterior_grid.pdf"
        blob_other = Mock()
        blob_other.name = "path/outputs/ts/other_file.csv"
        mock_bucket.list_blobs.return_value = [blob_match, blob_other]

        result = find_matching_blobs(
            mock_client, "bucket", "path", ["posterior_grid.pdf"]
        )
        assert result == [blob_match]

    def test_no_match(self):
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket

        blob = Mock()
        blob.name = "path/outputs/other.csv"
        mock_bucket.list_blobs.return_value = [blob]

        result = find_matching_blobs(
            mock_client, "bucket", "path", ["posterior_grid.pdf"]
        )
        assert result == []

    def test_finds_across_timestamped_subdirs(self):
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client.bucket.return_value = mock_bucket

        blob1 = Mock()
        blob1.name = "path/outputs/20250101/posterior_grid.pdf"
        blob2 = Mock()
        blob2.name = "path/outputs/20250102/posterior_grid.pdf"
        mock_bucket.list_blobs.return_value = [blob1, blob2]

        result = find_matching_blobs(
            mock_client, "bucket", "path", ["posterior_grid.pdf"]
        )
        assert len(result) == 2


class TestExtractScanPrefix:
    """Test extract_scan_prefix function."""

    def test_exact_pattern(self):
        assert extract_scan_prefix(["test/reff_resimm_beta"]) == "test/reff_resimm_beta"

    def test_wildcard_after_slash(self):
        assert extract_scan_prefix(["202605/*"]) == "202605"

    def test_wildcard_in_middle(self):
        assert extract_scan_prefix(["202605/hosp_*"]) == "202605"

    def test_star_only(self):
        assert extract_scan_prefix(["*"]) == ""

    def test_trailing_slash_patterns(self):
        # Patterns generated from "testdir/myexp01/"
        assert extract_scan_prefix(["testdir/myexp01/*", "testdir/myexp01"]) == "testdir/myexp01"

    def test_nested_wildcard(self):
        assert extract_scan_prefix(["test/myexperiments/*"]) == "test/myexperiments"

    def test_empty_patterns(self):
        assert extract_scan_prefix([]) == ""

    def test_question_mark_wildcard(self):
        assert extract_scan_prefix(["202605/exp?"]) == "202605"
