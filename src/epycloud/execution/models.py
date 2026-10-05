"""Data models shared by execution backends and command handlers."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal


class RunState(StrEnum):
    """Normalized state for a pipeline run or stage job."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class StageResources:
    """Resolved resources for one logical pipeline stage."""

    machine_type: str
    cpu_milli: int
    memory_mib: int
    max_run_duration: int


@dataclass(frozen=True)
class PipelineRunSpec:
    """Provider-neutral inputs required to launch a complete pipeline."""

    experiment_id: str
    run_id: str | None
    storage_bucket: str
    storage_prefix: str
    forecast_repo: str
    forecast_repo_ref: str
    image_tag: str
    execution_identity: str
    max_parallelism: int
    task_count_per_node: int
    stage_resources: dict[str, StageResources]
    compute_region: str = ""
    stage_candidates: dict[str, tuple[StageResources, ...]] = field(default_factory=dict)
    stage_pinned: dict[str, bool] = field(default_factory=dict)
    profile: str = ""
    billing_project: str = ""
    skip_output: bool = False
    output_config: str | None = None


@dataclass(frozen=True)
class StageJobSpec:
    """Provider-neutral inputs required to launch one pipeline stage."""

    job_id: str
    stage: str
    experiment_id: str
    run_id: str
    task_index: int
    num_tasks: int | None
    output_config: str | None
    image_uri: str
    storage_bucket: str
    storage_prefix: str
    forecast_repo: str
    resources: StageResources
    task_count_per_node: int
    execution_identity: str
    profile: str = ""
    billing_project: str = ""
    skip_existing: bool = False


@dataclass(frozen=True)
class SubmissionPlan:
    """A side-effect-free description of a provider submission."""

    provider: str
    operation: Literal["pipeline", "job"]
    target: str
    payload: dict[str, Any]
    display_details: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunRef:
    """Stable reference returned after a provider accepts work."""

    provider: str
    kind: Literal["pipeline", "job"]
    run_id: str
    resource_name: str


@dataclass(frozen=True)
class RunRecord:
    """Normalized provider record retaining the original response."""

    ref: RunRef
    state: RunState
    raw: dict[str, Any]


@dataclass(frozen=True)
class RunQuery:
    """Filters supported when listing pipeline runs."""

    limit: int | None = None
    status: str | None = None
    since: datetime | None = None
    experiment_id: str | None = None


@dataclass(frozen=True)
class ChildCancellation:
    """Cancellation outcome for a child stage job."""

    job_id: str
    outcome: Literal["cancelled", "not_found", "already_complete", "failed"]
    status_code: int | None = None
    message: str = ""


@dataclass(frozen=True)
class CancelResult:
    """Result of cancelling a pipeline and its child jobs."""

    run_ref: RunRef
    children: tuple[ChildCancellation, ...] = ()
