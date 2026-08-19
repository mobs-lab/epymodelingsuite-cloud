"""Tests for occupancy-based Cloud Batch provisioning warnings."""

from datetime import UTC, datetime, timedelta

from epycloud.cli import create_parser
from epycloud.commands.status.operations import (
    ProvisioningAlert,
    ProvisioningStallTracker,
    detect_one_shot_provisioning_alerts,
    display_status,
    extract_requested_parallelism,
    extract_task_count,
    extract_task_counts,
)

NOW = datetime(2026, 8, 19, 16, 0, tzinfo=UTC)


def test_status_parser_exposes_stall_threshold():
    args = create_parser().parse_args(["status", "--stall-threshold", "25"])

    assert args.stall_threshold == 25


def batch_job(
    *,
    counts: dict[str, int | str] | None = None,
    task_count: int | str = 10,
    parallelism: int | str | None = 10,
    created_at: datetime | None = None,
    state: str = "RUNNING",
    status_events: list[dict] | None = None,
) -> dict:
    """Build a representative gcloud Batch job document."""
    task_group = {"taskCount": task_count, "taskSpec": {}}
    if parallelism is not None:
        task_group["parallelism"] = parallelism
    return {
        "name": "projects/test/locations/us-central1/jobs/stage-b-deadbeef",
        "createTime": (created_at or NOW).isoformat(),
        "labels": {"stage": "runner", "exp_id": "test-exp"},
        "taskGroups": [task_group],
        "status": {
            "state": state,
            "taskGroups": {"group0": {"counts": counts or {}}},
            "statusEvents": status_events or [],
        },
    }


def test_extract_task_counts_normalizes_case_and_int64_strings():
    job = batch_job(
        counts={
            "succeeded": "2",
            "FAILED": "1",
            "running": "3",
            "ASSIGNED": "4",
            "pending": "5",
        }
    )

    assert extract_task_counts(job) == {
        "SUCCEEDED": 2,
        "FAILED": 1,
        "RUNNING": 3,
        "ASSIGNED": 4,
        "PENDING": 5,
    }


def test_requested_parallelism_and_task_count_coerce_strings():
    job = batch_job(task_count="52", parallelism="10")

    assert extract_task_count(job) == 52
    assert extract_requested_parallelism(job) == 10


def test_requested_parallelism_falls_back_to_task_count():
    job = batch_job(task_count="52", parallelism=None)

    assert extract_requested_parallelism(job) == 52


def test_one_shot_detects_aged_zero_fill_with_empty_counts():
    job = batch_job(counts={}, created_at=NOW - timedelta(minutes=20))

    alerts = detect_one_shot_provisioning_alerts([job], 15, now=NOW)

    assert alerts == [
        ProvisioningAlert(
            job_name="stage-b-deadbeef",
            stage="runner",
            occupied=0,
            demand=10,
            duration_seconds=1200,
            stalled=True,
            resource_exhausted=False,
        )
    ]


def test_one_shot_respects_zero_fill_grace_period():
    job = batch_job(counts={}, created_at=NOW - timedelta(minutes=14))

    assert detect_one_shot_provisioning_alerts([job], 15, now=NOW) == []


def test_one_shot_reports_partial_underfill_with_unknown_duration():
    job = batch_job(
        counts={"SUCCEEDED": "2", "RUNNING": "3", "PENDING": "5"},
        created_at=NOW - timedelta(hours=4),
    )

    alerts = detect_one_shot_provisioning_alerts([job], 15, now=NOW)

    assert len(alerts) == 1
    assert alerts[0].occupied == 3
    assert alerts[0].demand == 8
    assert alerts[0].duration_seconds is None
    assert alerts[0].stalled is False


def test_detection_uses_requested_parallelism_not_total_task_count():
    job = batch_job(
        counts={"RUNNING": "10", "PENDING": "42"},
        task_count="52",
        parallelism="10",
        created_at=NOW - timedelta(hours=1),
    )

    assert detect_one_shot_provisioning_alerts([job], 15, now=NOW) == []


def test_assigned_tasks_count_as_occupied_slots():
    job = batch_job(
        counts={"ASSIGNED": "10"},
        created_at=NOW - timedelta(hours=1),
    )

    assert detect_one_shot_provisioning_alerts([job], 15, now=NOW) == []


def test_detection_reduces_demand_as_tasks_complete():
    job = batch_job(
        counts={"SUCCEEDED": "8", "RUNNING": "2"},
        task_count="10",
        parallelism="10",
        created_at=NOW - timedelta(hours=1),
    )

    assert detect_one_shot_provisioning_alerts([job], 15, now=NOW) == []


def test_pending_is_not_required_to_detect_underfill():
    job = batch_job(
        counts={"RUNNING": "2"},
        created_at=NOW - timedelta(hours=1),
    )

    alerts = detect_one_shot_provisioning_alerts([job], 15, now=NOW)

    assert len(alerts) == 1
    assert alerts[0].occupied == 2
    assert alerts[0].demand == 10


def test_watch_waits_for_observed_partial_fill_stall_duration():
    job = batch_job(
        counts={"RUNNING": "2"},
        created_at=NOW - timedelta(hours=4),
    )
    tracker = ProvisioningStallTracker(15)

    assert tracker.observe([job], now=NOW) == []
    assert tracker.observe([job], now=NOW + timedelta(minutes=14)) == []
    alerts = tracker.observe([job], now=NOW + timedelta(minutes=15))

    assert len(alerts) == 1
    assert alerts[0].duration_seconds == 900


def test_watch_resets_timer_when_completion_or_occupancy_changes():
    tracker = ProvisioningStallTracker(15)
    initial = batch_job(counts={"RUNNING": "2"})
    progressed = batch_job(counts={"SUCCEEDED": "1", "RUNNING": "3"})

    assert tracker.observe([initial], now=NOW) == []
    assert tracker.observe([initial], now=NOW + timedelta(minutes=14)) == []
    assert tracker.observe([progressed], now=NOW + timedelta(minutes=15)) == []
    assert tracker.observe([progressed], now=NOW + timedelta(minutes=29)) == []
    assert len(tracker.observe([progressed], now=NOW + timedelta(minutes=30))) == 1


def test_watch_uses_job_age_only_when_no_task_has_started():
    job = batch_job(counts={}, created_at=NOW - timedelta(minutes=20))
    tracker = ProvisioningStallTracker(15)

    alerts = tracker.observe([job], now=NOW)

    assert len(alerts) == 1
    assert alerts[0].duration_seconds == 1200


def test_resource_exhaustion_event_does_not_bypass_grace_period():
    job = batch_job(
        counts={},
        created_at=NOW - timedelta(minutes=5),
        status_events=[{"description": "CODE_GCE_ZONE_RESOURCE_POOL_EXHAUSTED"}],
    )

    assert detect_one_shot_provisioning_alerts([job], 15, now=NOW) == []


def test_display_separates_completed_tasks_slots_and_warnings(capsys):
    job = batch_job(
        counts={},
        created_at=NOW - timedelta(minutes=20),
        status_events=[{"description": "CODE_GCE_ZONE_RESOURCE_POOL_EXHAUSTED"}],
    )
    alert = detect_one_shot_provisioning_alerts([job], 15, now=NOW)

    display_status([], [job], None, provisioning_alerts=alert)

    output = capsys.readouterr().out
    assert "TASKS" in output
    assert "SLOTS" in output
    assert "0/10" in output
    assert "Provisioning warnings" in output
    assert "provisioning stalled for 20m" in output
    assert "zone resource pool exhaustion" in output
