"""Provider-neutral execution backends for cloud pipeline operations."""

from .base import ExecutionAuthenticationError, ExecutionBackend, ExecutionBackendError
from .factory import get_execution_backend, get_execution_provider
from .models import (
    CancelResult,
    ChildCancellation,
    PipelineRunSpec,
    RunQuery,
    RunRecord,
    RunRef,
    RunState,
    StageJobSpec,
    StageResources,
    SubmissionPlan,
)

__all__ = [
    "CancelResult",
    "ChildCancellation",
    "ExecutionBackend",
    "ExecutionBackendError",
    "ExecutionAuthenticationError",
    "PipelineRunSpec",
    "RunQuery",
    "RunRecord",
    "RunRef",
    "RunState",
    "StageJobSpec",
    "StageResources",
    "SubmissionPlan",
    "get_execution_backend",
    "get_execution_provider",
]
