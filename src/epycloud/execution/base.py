"""Execution backend contract."""

from typing import Protocol

from epycloud.exceptions import EpycloudError

from .models import (
    CancelResult,
    PipelineRunSpec,
    RunQuery,
    RunRecord,
    RunRef,
    StageJobSpec,
    SubmissionPlan,
)


class ExecutionBackendError(EpycloudError):
    """A provider operation failed before returning a usable resource."""

    def __init__(self, message: str, provider: str, operation: str, returncode: int | None = None):
        details: dict[str, object] = {"provider": provider, "operation": operation}
        if returncode is not None:
            details["returncode"] = returncode
        super().__init__(message, details)
        self.provider = provider
        self.operation = operation
        self.returncode = returncode


class ExecutionAuthenticationError(EpycloudError):
    """Authentication failed before an execution-provider operation."""

    def __init__(self, message: str, provider: str):
        super().__init__(message)
        self.provider = provider


class ExecutionBackend(Protocol):
    """Operations needed to submit and manage cloud pipeline runs."""

    provider: str

    def plan_pipeline(self, spec: PipelineRunSpec) -> SubmissionPlan: ...

    def submit_pipeline(self, plan: SubmissionPlan) -> RunRef: ...

    def plan_job(self, spec: StageJobSpec) -> SubmissionPlan: ...

    def submit_job(self, plan: SubmissionPlan) -> RunRef: ...

    def list_runs(self, query: RunQuery) -> list[RunRecord]: ...

    def describe_run(self, execution_id: str) -> RunRecord: ...

    def resolve_run_ref(self, execution_id: str) -> RunRef: ...

    def cancel_run(self, execution_id: str, include_jobs: bool = True) -> CancelResult: ...

    def plan_retry(self, execution_id: str) -> SubmissionPlan: ...
