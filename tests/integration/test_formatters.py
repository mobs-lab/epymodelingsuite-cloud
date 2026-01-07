"""Integration tests for formatters module."""

import argparse
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from epycloud.lib.formatters import (
    CapitalizedHelpFormatter,
    create_subparsers,
    format_duration,
    format_severity,
    format_status,
    format_table,
    format_timestamp,
    format_timestamp_full,
    format_timestamp_time,
    parse_duration_string,
    parse_since_time,
)


class TestCapitalizedHelpFormatter:
    """Test CapitalizedHelpFormatter class."""

    def test_usage_prefix_capitalized(self):
        """Test that usage prefix is capitalized."""
        parser = argparse.ArgumentParser(formatter_class=CapitalizedHelpFormatter)
        parser.add_argument("--test", help="Test argument")

        help_text = parser.format_help()

        # Should have "Usage:" (capitalized) with newline
        assert "Usage:\n" in help_text


class TestCreateSubparsers:
    """Test create_subparsers function."""

    def test_create_subparsers_basic(self):
        """Test basic subparser creation."""
        parser = argparse.ArgumentParser()
        subparsers = create_subparsers(parser, "command")

        assert subparsers is not None
        assert hasattr(subparsers, "add_parser")

    def test_create_subparsers_with_custom_title(self):
        """Test subparser creation with custom title."""
        parser = argparse.ArgumentParser()
        subparsers = create_subparsers(parser, "command", title="Commands")

        assert subparsers is not None

    def test_subparser_has_capitalized_formatter(self):
        """Test that subparsers automatically get CapitalizedHelpFormatter."""
        parser = argparse.ArgumentParser()
        subparsers = create_subparsers(parser, "command")

        # Add a subcommand
        sub = subparsers.add_parser("test", help="Test command")

        # Should have CapitalizedHelpFormatter
        assert sub.formatter_class == CapitalizedHelpFormatter

        # Should have "Options" title
        assert sub._optionals.title == "Options"

    def test_subparser_respects_custom_formatter(self):
        """Test that custom formatter_class is respected."""
        parser = argparse.ArgumentParser()
        subparsers = create_subparsers(parser, "command")

        # Add subcommand with custom formatter
        sub = subparsers.add_parser(
            "test",
            help="Test command",
            formatter_class=argparse.RawTextHelpFormatter
        )

        # Should use custom formatter
        assert sub.formatter_class == argparse.RawTextHelpFormatter


class TestFormatTimestamp:
    """Test timestamp formatting functions."""

    def test_format_timestamp_full(self):
        """Test full timestamp formatting."""
        result = format_timestamp("2025-11-07T10:30:00Z", "full")
        assert result == "2025-11-07 10:30:00"

    def test_format_timestamp_time(self):
        """Test time-only formatting."""
        result = format_timestamp("2025-11-07T10:30:00Z", "time")
        assert result == "10:30:00"

    def test_format_timestamp_default(self):
        """Test default formatting (full)."""
        result = format_timestamp("2025-11-07T10:30:00Z")
        assert result == "2025-11-07 10:30:00"

    def test_format_timestamp_invalid_format(self):
        """Test invalid format defaults to full."""
        result = format_timestamp("2025-11-07T10:30:00Z", "invalid")
        assert result == "2025-11-07 10:30:00"


class TestFormatTimestampFull:
    """Test format_timestamp_full function."""

    def test_format_timestamp_full_basic(self):
        """Test basic timestamp formatting."""
        result = format_timestamp_full("2025-11-07T10:30:00Z")
        assert result == "2025-11-07 10:30:00"

    def test_format_timestamp_full_with_microseconds(self):
        """Test timestamp with microseconds."""
        result = format_timestamp_full("2025-11-07T10:30:00.123456Z")
        assert result == "2025-11-07 10:30:00"

    def test_format_timestamp_full_with_timezone(self):
        """Test timestamp with timezone offset."""
        result = format_timestamp_full("2025-11-07T10:30:00+05:00")
        assert result == "2025-11-07 10:30:00"

    def test_format_timestamp_full_invalid_string(self):
        """Test invalid timestamp string fallback."""
        result = format_timestamp_full("invalid-timestamp")
        assert result == "invalid-timestamp"

    def test_format_timestamp_full_short_string(self):
        """Test short string fallback."""
        result = format_timestamp_full("short")
        assert result == "short"

    def test_format_timestamp_full_none(self):
        """Test None input."""
        result = format_timestamp_full(None)
        assert result is None

    def test_format_timestamp_full_empty_string(self):
        """Test empty string input."""
        result = format_timestamp_full("")
        assert result == ""


class TestFormatTimestampTime:
    """Test format_timestamp_time function."""

    def test_format_timestamp_time_basic(self):
        """Test basic time formatting."""
        result = format_timestamp_time("2025-11-07T10:30:00Z")
        assert result == "10:30:00"

    def test_format_timestamp_time_with_microseconds(self):
        """Test time with microseconds."""
        result = format_timestamp_time("2025-11-07T14:45:30.123456Z")
        assert result == "14:45:30"

    def test_format_timestamp_time_invalid_string(self):
        """Test invalid timestamp string fallback."""
        result = format_timestamp_time("2025-11-07T10:30:00Z-invalid")
        assert result == "10:30:00"

    def test_format_timestamp_time_short_string(self):
        """Test short string fallback."""
        result = format_timestamp_time("short")
        assert result == "short"


class TestFormatDuration:
    """Test format_duration function."""

    def test_format_duration_seconds(self):
        """Test duration in seconds."""
        start = "2025-11-07T10:00:00Z"
        end = "2025-11-07T10:00:45Z"
        result = format_duration(start, end)
        assert result == "45s"

    def test_format_duration_minutes(self):
        """Test duration in minutes."""
        start = "2025-11-07T10:00:00Z"
        end = "2025-11-07T10:05:00Z"
        result = format_duration(start, end)
        assert result == "5m"

    def test_format_duration_minutes_with_seconds(self):
        """Test duration with minutes and seconds."""
        start = "2025-11-07T10:00:00Z"
        end = "2025-11-07T10:05:30Z"
        result = format_duration(start, end)
        assert result == "5m 30s"

    def test_format_duration_hours(self):
        """Test duration in hours."""
        start = "2025-11-07T10:00:00Z"
        end = "2025-11-07T12:00:00Z"
        result = format_duration(start, end)
        assert result == "2h"

    def test_format_duration_hours_with_minutes(self):
        """Test duration with hours and minutes."""
        start = "2025-11-07T10:00:00Z"
        end = "2025-11-07T12:30:00Z"
        result = format_duration(start, end)
        assert result == "2h 30m"

    def test_format_duration_days(self):
        """Test duration in days."""
        start = "2025-11-07T10:00:00Z"
        end = "2025-11-09T10:00:00Z"
        result = format_duration(start, end)
        assert result == "2d"

    def test_format_duration_days_with_hours(self):
        """Test duration with days and hours."""
        start = "2025-11-07T10:00:00Z"
        end = "2025-11-08T13:00:00Z"
        result = format_duration(start, end)
        assert result == "1d 3h"

    def test_format_duration_negative(self):
        """Test negative duration (end before start)."""
        start = "2025-11-07T12:00:00Z"
        end = "2025-11-07T10:00:00Z"
        result = format_duration(start, end)
        assert result == "0s"

    def test_format_duration_no_end(self):
        """Test duration with no end time (uses current time)."""
        # Mock current time
        with patch("epycloud.lib.formatters.datetime") as mock_datetime:
            mock_now = datetime(2025, 11, 7, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat

            start = "2025-11-07T10:00:00Z"
            result = format_duration(start, None)
            assert result == "2h"

    def test_format_duration_invalid_start(self):
        """Test invalid start time."""
        result = format_duration("invalid", "2025-11-07T10:00:00Z")
        assert result == "unknown"

    def test_format_duration_invalid_end(self):
        """Test invalid end time."""
        result = format_duration("2025-11-07T10:00:00Z", "invalid")
        assert result == "unknown"


class TestFormatStatus:
    """Test format_status function."""

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_succeeded(self, mock_color):
        """Test SUCCEEDED status formatting."""
        mock_color.return_value = True
        result = format_status("SUCCEEDED")
        assert result == "\033[32mSUCCEEDED\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_completed(self, mock_color):
        """Test COMPLETED status formatting."""
        mock_color.return_value = True
        result = format_status("COMPLETED")
        assert result == "\033[32mCOMPLETED\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_failed(self, mock_color):
        """Test FAILED status formatting."""
        mock_color.return_value = True
        result = format_status("FAILED")
        assert result == "\033[31mFAILED\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_cancelled(self, mock_color):
        """Test CANCELLED status formatting."""
        mock_color.return_value = True
        result = format_status("CANCELLED")
        assert result == "\033[31mCANCELLED\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_active(self, mock_color):
        """Test ACTIVE status formatting."""
        mock_color.return_value = True
        result = format_status("ACTIVE")
        assert result == "\033[33mACTIVE\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_running(self, mock_color):
        """Test RUNNING status formatting."""
        mock_color.return_value = True
        result = format_status("RUNNING")
        assert result == "\033[33mRUNNING\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_pending(self, mock_color):
        """Test PENDING status formatting."""
        mock_color.return_value = True
        result = format_status("PENDING")
        assert result == "\033[33mPENDING\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_scheduled(self, mock_color):
        """Test SCHEDULED status formatting."""
        mock_color.return_value = True
        result = format_status("SCHEDULED")
        assert result == "\033[36mSCHEDULED\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_unknown(self, mock_color):
        """Test unknown status (no color)."""
        mock_color.return_value = True
        result = format_status("UNKNOWN")
        assert result == "UNKNOWN"

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_no_color(self, mock_color):
        """Test status without color support."""
        mock_color.return_value = False
        result = format_status("SUCCEEDED")
        assert result == "SUCCEEDED"
        assert "\033[" not in result

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_case_insensitive(self, mock_color):
        """Test status formatting is case-insensitive."""
        mock_color.return_value = True
        result = format_status("succeeded")
        assert result == "\033[32msucceeded\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_batch_type(self, mock_color):
        """Test batch status type."""
        mock_color.return_value = True
        result = format_status("RUNNING", "batch")
        assert result == "\033[33mRUNNING\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_status_none(self, mock_color):
        """Test None status."""
        mock_color.return_value = True
        result = format_status(None)
        assert result is None


class TestFormatSeverity:
    """Test format_severity function."""

    @patch("epycloud.lib.output.supports_color")
    def test_format_severity_error(self, mock_color):
        """Test ERROR severity formatting."""
        mock_color.return_value = True
        result = format_severity("ERROR")
        assert result == "\033[31mERROR\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_severity_critical(self, mock_color):
        """Test CRITICAL severity formatting."""
        mock_color.return_value = True
        result = format_severity("CRITICAL")
        assert result == "\033[31mCRITICAL\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_severity_warning(self, mock_color):
        """Test WARNING severity formatting."""
        mock_color.return_value = True
        result = format_severity("WARNING")
        assert result == "\033[33mWARNING\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_severity_info(self, mock_color):
        """Test INFO severity formatting."""
        mock_color.return_value = True
        result = format_severity("INFO")
        assert result == "\033[34mINFO\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_severity_debug(self, mock_color):
        """Test DEBUG severity formatting."""
        mock_color.return_value = True
        result = format_severity("DEBUG")
        assert result == "\033[36mDEBUG\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_severity_notice(self, mock_color):
        """Test NOTICE severity formatting."""
        mock_color.return_value = True
        result = format_severity("NOTICE")
        assert result == "\033[33mNOTICE\033[0m"

    @patch("epycloud.lib.output.supports_color")
    def test_format_severity_no_color(self, mock_color):
        """Test severity without color support."""
        mock_color.return_value = False
        result = format_severity("ERROR")
        assert result == "ERROR"
        assert "\033[" not in result

    @patch("epycloud.lib.output.supports_color")
    def test_format_severity_case_insensitive(self, mock_color):
        """Test severity formatting is case-insensitive."""
        mock_color.return_value = True
        result = format_severity("error")
        assert result == "\033[31merror\033[0m"


class TestFormatTable:
    """Test format_table function."""

    def test_format_table_basic(self):
        """Test basic table formatting."""
        headers = ["Name", "Age", "City"]
        rows = [["Alice", "30", "NYC"], ["Bob", "25", "SF"]]
        result = format_table(headers, rows)

        lines = result.split("\n")
        assert len(lines) == 4  # header + separator + 2 rows
        assert "Name" in lines[0]
        assert "Age" in lines[0]
        assert "City" in lines[0]
        assert "Alice" in lines[2]
        assert "Bob" in lines[3]

    def test_format_table_with_fixed_widths(self):
        """Test table with fixed column widths."""
        headers = ["Name", "Age"]
        rows = [["Alice", "30"], ["Bob", "25"]]
        result = format_table(headers, rows, column_widths=[10, 5])

        lines = result.split("\n")
        # First row should have fixed widths
        assert "Name" in lines[0]
        # Separator should match total width
        assert len(lines[1]) > 10

    def test_format_table_auto_width(self):
        """Test table with auto-calculated widths."""
        headers = ["Name", "Age"]
        rows = [["Alice", "30"], ["VeryLongName", "25"]]
        result = format_table(headers, rows)

        lines = result.split("\n")
        # Width should accommodate longest value
        assert "VeryLongName" in lines[3]

    def test_format_table_empty_headers(self):
        """Test table with empty headers."""
        result = format_table([], [["data"]])
        assert result == ""

    def test_format_table_empty_rows(self):
        """Test table with empty rows."""
        result = format_table(["Header"], [])
        assert result == ""

    def test_format_table_single_column(self):
        """Test table with single column."""
        headers = ["Name"]
        rows = [["Alice"], ["Bob"]]
        result = format_table(headers, rows)

        lines = result.split("\n")
        assert len(lines) == 4
        assert "Alice" in result
        assert "Bob" in result

    def test_format_table_varying_row_lengths(self):
        """Test table with varying row lengths."""
        headers = ["A", "B", "C"]
        rows = [["1", "2"], ["3", "4", "5"]]  # Different lengths
        result = format_table(headers, rows)

        # Should handle gracefully
        assert "1" in result
        assert "5" in result


class TestParseSinceTime:
    """Test parse_since_time function."""

    def test_parse_since_time_hours(self):
        """Test parsing hours."""
        result = parse_since_time("2h")
        assert result is not None
        # Should be 2 hours ago from now
        expected = datetime.now(UTC) - timedelta(hours=2)
        assert abs((result - expected).total_seconds()) < 2

    def test_parse_since_time_minutes(self):
        """Test parsing minutes."""
        result = parse_since_time("30m")
        assert result is not None
        expected = datetime.now(UTC) - timedelta(minutes=30)
        assert abs((result - expected).total_seconds()) < 2

    def test_parse_since_time_days(self):
        """Test parsing days."""
        result = parse_since_time("2d")
        assert result is not None
        expected = datetime.now(UTC) - timedelta(days=2)
        assert abs((result - expected).total_seconds()) < 2

    def test_parse_since_time_seconds(self):
        """Test parsing seconds."""
        result = parse_since_time("45s")
        assert result is not None
        expected = datetime.now(UTC) - timedelta(seconds=45)
        assert abs((result - expected).total_seconds()) < 2

    def test_parse_since_time_iso_timestamp(self):
        """Test parsing ISO timestamp."""
        result = parse_since_time("2025-11-07T10:30:00Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 7

    def test_parse_since_time_empty(self):
        """Test parsing empty string."""
        result = parse_since_time("")
        assert result is None

    def test_parse_since_time_none(self):
        """Test parsing None."""
        result = parse_since_time(None)
        assert result is None

    def test_parse_since_time_invalid_format(self):
        """Test parsing invalid format."""
        result = parse_since_time("invalid")
        assert result is None

    def test_parse_since_time_invalid_number(self):
        """Test parsing invalid number."""
        result = parse_since_time("ABCh")
        assert result is None


class TestParseDurationString:
    """Test parse_duration_string function."""

    def test_parse_duration_hours(self):
        """Test parsing hours."""
        result = parse_duration_string("2h")
        assert result == timedelta(hours=2)

    def test_parse_duration_minutes(self):
        """Test parsing minutes."""
        result = parse_duration_string("30m")
        assert result == timedelta(minutes=30)

    def test_parse_duration_days(self):
        """Test parsing days."""
        result = parse_duration_string("1d")
        assert result == timedelta(days=1)

    def test_parse_duration_seconds(self):
        """Test parsing seconds."""
        result = parse_duration_string("45s")
        assert result == timedelta(seconds=45)

    def test_parse_duration_empty(self):
        """Test parsing empty string."""
        result = parse_duration_string("")
        assert result is None

    def test_parse_duration_none(self):
        """Test parsing None."""
        result = parse_duration_string(None)
        assert result is None

    def test_parse_duration_no_unit(self):
        """Test parsing string without unit."""
        result = parse_duration_string("123")
        assert result is None

    def test_parse_duration_invalid_unit(self):
        """Test parsing invalid unit."""
        result = parse_duration_string("10x")
        assert result is None

    def test_parse_duration_invalid_number(self):
        """Test parsing invalid number."""
        result = parse_duration_string("ABCh")
        assert result is None
