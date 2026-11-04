"""Prove independent status reads overlap without timing assumptions."""

import subprocess
from datetime import UTC, datetime
from threading import Barrier
from unittest.mock import patch

from epycloud.commands.status.handlers import _fetch_status
from epycloud.commands.status.operations import fetch_active_batch_jobs


def test_status_sources_run_concurrently():
    barrier = Barrier(4, timeout=3)

    def fetch(**kwargs):
        barrier.wait()
        return []

    with patch("epycloud.commands.status.handlers.fetch_active_workflows", fetch), patch(
        "epycloud.commands.status.handlers.fetch_active_batch_jobs", fetch
    ), patch("epycloud.commands.status.handlers.fetch_recent_workflows", fetch), patch(
        "epycloud.commands.status.handlers.fetch_recent_batch_jobs", fetch
    ):
        assert _fetch_status(
            "p", "us-central1", ("us-east4",), None, False,
            datetime.now(UTC), "workflow",
        ) == ([], [], [], [])


def test_batch_regions_run_concurrently():
    barrier = Barrier(2, timeout=3)

    def run(command, **kwargs):
        barrier.wait()
        assert kwargs["timeout"] == 30
        return subprocess.CompletedProcess(command, 0, stdout='[{"name": "job"}]')

    with patch("epycloud.commands.status.operations.subprocess.run", run):
        jobs = fetch_active_batch_jobs("p", ("us-east4", "us-central1"), None, False)
    assert [job["region"] for job in jobs] == ["us-central1", "us-east4"]


def test_workflows_share_one_token_per_refresh():
    barrier = Barrier(2, timeout=3)

    def fetch(**kwargs):
        barrier.wait()
        assert kwargs["token_provider"]() == "token"
        return []

    with patch("epycloud.commands.status.handlers.get_gcloud_access_token", return_value="token") as token, patch(
        "epycloud.commands.status.handlers.fetch_active_workflows", fetch
    ), patch("epycloud.commands.status.handlers.fetch_recent_workflows", fetch), patch(
        "epycloud.commands.status.handlers.fetch_active_batch_jobs", return_value=[]
    ), patch("epycloud.commands.status.handlers.fetch_recent_batch_jobs", return_value=[]):
        for _ in range(2):
            _fetch_status("p", "r", ("r",), None, False, datetime.now(UTC), "workflow")
    assert token.call_count == 2


def test_recent_workflows_pagination_and_timezone():
    from unittest.mock import Mock

    from epycloud.commands.status.operations import fetch_recent_workflows

    pages = [
        {"executions": [{"name": "first", "endTime": "2026-11-04T11:00:00-05:00"}],
         "nextPageToken": "next"},
        {"executions": [{"name": "second", "endTime": "2026-11-04T16:01:00Z"}]},
    ]
    with patch("epycloud.commands.status.operations.requests.get",
               side_effect=[Mock(json=Mock(return_value=p)) for p in pages]) as get:
        jobs = fetch_recent_workflows(
            "p", "r", None, datetime(2026, 11, 4, 16, tzinfo=UTC), False,
            token_provider=lambda: "token",
        )
    assert {job["name"] for job in jobs} == {"first", "second"}
    assert get.call_args.kwargs["params"]["pageToken"] == "next"
    assert 'endTime>=' in get.call_args.kwargs["params"]["filter"]
