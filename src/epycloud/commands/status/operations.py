"""Interpret Batch job state and detect provisioning stalls."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

TASK_COUNT_STATES = ("SUCCEEDED", "FAILED", "RUNNING", "ASSIGNED", "PENDING")
ACTIVE_BATCH_STATES = frozenset({"RUNNING", "SCHEDULED", "QUEUED"})


def get_job_region(job: dict[str, Any]) -> str:
    """Return the annotated region or derive it from a full Batch job name."""
    if job.get("region"):
        return str(job["region"])
    parts = str(job.get("name", "")).split("/")
    try:
        return parts[parts.index("locations") + 1]
    except (ValueError, IndexError):
        return "unknown"


def _as_int(value: Any) -> int:
    """Coerce a Batch API integer value, returning zero for malformed data."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def extract_task_counts(job: dict[str, Any]) -> dict[str, int]:
    """Extract normalized counts for the first Batch task group."""
    task_groups = job.get("status", {}).get("taskGroups", {})
    if isinstance(task_groups, dict):
        first_group = next(iter(task_groups.values()), {})
    elif isinstance(task_groups, list):
        first_group = task_groups[0] if task_groups else {}
    else:
        first_group = {}

    raw_counts = first_group.get("counts", {}) if isinstance(first_group, dict) else {}
    if not isinstance(raw_counts, dict):
        raw_counts = {}
    normalized = {str(key).upper(): value for key, value in raw_counts.items()}
    return {state: _as_int(normalized.get(state, 0)) for state in TASK_COUNT_STATES}


def extract_task_count(job: dict[str, Any]) -> int:
    """Return the configured task count for the first task group."""
    task_groups = job.get("taskGroups", [])
    if not isinstance(task_groups, list) or not task_groups:
        return 0
    first_group = task_groups[0]
    return _as_int(first_group.get("taskCount", 0)) if isinstance(first_group, dict) else 0


def extract_requested_parallelism(job: dict[str, Any]) -> int:
    """Return requested parallelism, falling back to the task count."""
    task_groups = job.get("taskGroups", [])
    if not isinstance(task_groups, list) or not task_groups:
        return 0
    first_group = task_groups[0]
    if not isinstance(first_group, dict):
        return 0
    return _as_int(first_group.get("parallelism")) or _as_int(first_group.get("taskCount"))


@dataclass(frozen=True)
class ProvisioningAlert:
    """An underfilled Batch job that may be stalled on VM provisioning."""

    job_name: str
    stage: str
    occupied: int
    demand: int
    duration_seconds: float | None
    stalled: bool
    resource_exhausted: bool


@dataclass(frozen=True)
class _JobSnapshot:
    """Occupancy values used to evaluate provisioning progress."""

    completed: int
    occupied: int
    demand: int
    underfilled: bool


@dataclass
class _JobProgress:
    """Last observed Batch counts and the time they changed."""

    completed: int
    occupied: int
    last_progress_at: datetime


def _job_snapshot(job: dict[str, Any]) -> _JobSnapshot:
    counts = extract_task_counts(job)
    completed = counts["SUCCEEDED"] + counts["FAILED"]
    occupied = counts["RUNNING"] + counts["ASSIGNED"]
    task_count = extract_task_count(job)
    requested = extract_requested_parallelism(job)
    remaining = max(task_count - completed, 0)
    demand = min(requested, remaining)
    state = str(job.get("status", {}).get("state", "UNKNOWN")).upper()
    underfilled = state in ACTIVE_BATCH_STATES and demand > 0 and occupied < demand
    return _JobSnapshot(completed, occupied, demand, underfilled)


def _parse_api_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _reported_resource_exhaustion(job: dict[str, Any]) -> bool:
    events = job.get("status", {}).get("statusEvents", [])
    event_text = json.dumps(events).upper()
    return "RESOURCE_POOL_EXHAUSTED" in event_text


def _build_alert(
    job: dict[str, Any],
    snapshot: _JobSnapshot,
    duration_seconds: float | None,
    stalled: bool,
) -> ProvisioningAlert:
    job_name = job.get("name", "").split("/")[-1] or "unknown"
    stage = job.get("labels", {}).get("stage", "unknown")
    return ProvisioningAlert(
        job_name=job_name,
        stage=stage,
        occupied=snapshot.occupied,
        demand=snapshot.demand,
        duration_seconds=duration_seconds,
        stalled=stalled,
        resource_exhausted=_reported_resource_exhaustion(job),
    )


def detect_one_shot_provisioning_alerts(
    jobs: list[dict[str, Any]],
    threshold_minutes: int,
    now: datetime | None = None,
) -> list[ProvisioningAlert]:
    """Detect underfilled jobs without inventing progress history.

    A never-started job has a measurable stall duration equal to its age. For
    a partially filled job, one snapshot can report underfill but cannot say
    how long it has persisted.
    """
    observed_at = now or datetime.now(UTC)
    alerts: list[ProvisioningAlert] = []
    threshold_seconds = threshold_minutes * 60

    for job in jobs:
        snapshot = _job_snapshot(job)
        if not snapshot.underfilled:
            continue

        never_started = snapshot.completed == 0 and snapshot.occupied == 0
        if never_started:
            created_at = _parse_api_time(job.get("createTime", ""))
            if created_at is None:
                alerts.append(_build_alert(job, snapshot, None, stalled=False))
                continue
            duration_seconds = max((observed_at - created_at).total_seconds(), 0)
            if duration_seconds < threshold_seconds:
                continue
            alerts.append(_build_alert(job, snapshot, duration_seconds, stalled=True))
        else:
            alerts.append(_build_alert(job, snapshot, None, stalled=False))

    return alerts


class ProvisioningStallTracker:
    """Retain per-job occupancy history across status watch refreshes."""

    def __init__(self, threshold_minutes: int) -> None:
        self.threshold_seconds = threshold_minutes * 60
        self._progress: dict[str, _JobProgress] = {}

    def observe(
        self,
        jobs: list[dict[str, Any]],
        now: datetime | None = None,
    ) -> list[ProvisioningAlert]:
        """Record a watch sample and return jobs stalled beyond the grace period."""
        observed_at = now or datetime.now(UTC)
        alerts: list[ProvisioningAlert] = []
        active_keys: set[str] = set()

        for job in jobs:
            job_key = job.get("name", "")
            if not job_key:
                continue
            active_keys.add(job_key)
            snapshot = _job_snapshot(job)
            previous = self._progress.get(job_key)

            if previous is None:
                never_started = snapshot.completed == 0 and snapshot.occupied == 0
                created_at = _parse_api_time(job.get("createTime", "")) if never_started else None
                last_progress_at = created_at or observed_at
            elif (
                snapshot.completed != previous.completed
                or snapshot.occupied != previous.occupied
            ):
                last_progress_at = observed_at
            else:
                last_progress_at = previous.last_progress_at

            self._progress[job_key] = _JobProgress(
                completed=snapshot.completed,
                occupied=snapshot.occupied,
                last_progress_at=last_progress_at,
            )

            stalled_for = max((observed_at - last_progress_at).total_seconds(), 0)
            if snapshot.underfilled and stalled_for >= self.threshold_seconds:
                alerts.append(_build_alert(job, snapshot, stalled_for, stalled=True))

        for job_key in self._progress.keys() - active_keys:
            del self._progress[job_key]

        return alerts


def extract_image_tag(image_uri: str) -> str:
    """Extract tag from Docker image URI.

    Parameters
    ----------
    image_uri : str
        Full image URI (e.g., "us-central1-docker.pkg.dev/proj/repo/img:tag")

    Returns
    -------
    str
        Image tag, digest prefix, or "latest" if no tag specified
    """
    if not image_uri:
        return "unknown"

    if "@sha256:" in image_uri:
        # Digest reference - show first 7 chars of hash (like git)
        digest = image_uri.split("@sha256:")[-1]
        return f"sha256:{digest[:7]}"
    elif ":" in image_uri.split("/")[-1]:
        # Has explicit tag
        return image_uri.split(":")[-1]
    else:
        # No tag = implicit latest
        return "latest"
