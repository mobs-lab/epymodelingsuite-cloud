"""Google Cloud implementation of the execution backend."""

import contextlib
import json
import os
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import requests

from epycloud.commands.run.cloud.batch_config import build_batch_job_config
from epycloud.commands.workflow import api as default_workflow_api
from epycloud.lib.command_helpers import DEFAULT_WORKFLOW_NAME, get_gcloud_access_token
from epycloud.lib.validation import sanitize_label_value

from .base import ExecutionAuthenticationError, ExecutionBackendError
from .gcp_machines import (
    ARM_MACHINE_FAMILIES,
    HYPERDISK_MACHINE_FAMILIES,
    MACHINE_CHAINS_BY_REQUIREMENT,
    MACHINE_SPECS,
    STAGE_MACHINE_CHAINS,
    get_candidate_chain,
    get_machine_family,
    is_hyperdisk_family,
    validate_hyperdisk_family,
)
from .models import (
    CancelResult,
    ChildCancellation,
    PipelineRunSpec,
    RunQuery,
    RunRecord,
    RunRef,
    RunState,
    StageJobSpec,
    SubmissionPlan,
)

__all__ = [
    "ARM_MACHINE_FAMILIES",
    "HYPERDISK_MACHINE_FAMILIES",
    "MACHINE_CHAINS_BY_REQUIREMENT",
    "MACHINE_SPECS",
    "STAGE_MACHINE_CHAINS",
    "GcpExecutionBackend",
    "get_candidate_chain",
    "get_machine_family",
    "is_hyperdisk_family",
    "validate_hyperdisk_family",
]


class GcpExecutionBackend:
    """Execute pipeline operations using the existing GCP transports."""

    provider = "gcp"

    def __init__(
        self,
        config: dict[str, Any],
        *,
        verbose: bool = False,
        command_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        token_provider: Callable[[], str] | None = None,
        http_post: Callable[..., Any] | None = None,
        workflow_api: Any | None = None,
    ) -> None:
        google_cloud = config.get("google_cloud", {})
        self.project_id = google_cloud.get("project_id", "")
        self.region = google_cloud.get("region", "us-central1")
        configured_batch_regions = google_cloud.get("batch_regions")
        self.batch_regions = (
            tuple(configured_batch_regions)
            if isinstance(configured_batch_regions, dict) and configured_batch_regions
            else (self.region,)
        )
        self.workflow_name = google_cloud.get("workflow_name") or DEFAULT_WORKFLOW_NAME
        self.verbose = verbose
        self._command_runner = command_runner or subprocess.run
        self._token_provider = token_provider or (
            lambda: get_gcloud_access_token(verbose=self.verbose)
        )
        self._token: str | None = None
        self._http_post = http_post or requests.post
        self._workflow_api = workflow_api or default_workflow_api

    def plan_pipeline(self, spec: PipelineRunSpec) -> SubmissionPlan:
        """Build the exact legacy Workflows execution request without submitting it."""

        arguments: dict[str, Any] = {
            "bucket": spec.storage_bucket,
            "dirPrefix": spec.storage_prefix,
            "exp_id": spec.experiment_id,
            "githubForecastRepo": spec.forecast_repo,
            "batchSaEmail": spec.execution_identity,
            "imageTag": spec.image_tag,
        }

        if spec.profile:
            arguments["profile"] = sanitize_label_value(spec.profile)
        if spec.billing_project:
            arguments["billingProject"] = sanitize_label_value(spec.billing_project)
        if spec.run_id:
            arguments["runId"] = spec.run_id
        if spec.max_parallelism:
            arguments["maxParallelism"] = spec.max_parallelism
        if spec.task_count_per_node:
            arguments["taskCountPerNode"] = spec.task_count_per_node
        if spec.compute_region and spec.compute_region != self.region:
            arguments["batchLocation"] = spec.compute_region

        for stage in ("a", "b", "c"):
            candidates = spec.stage_candidates.get(stage) or (spec.stage_resources[stage],)
            resources = candidates[0]
            prefix = f"stage{stage.upper()}"
            if resources.machine_type:
                arguments[f"{prefix}MachineType"] = resources.machine_type
                arguments[f"{prefix}CpuMilli"] = resources.cpu_milli
                arguments[f"{prefix}MemoryMib"] = resources.memory_mib
            if stage in spec.stage_candidates:
                arguments[f"{prefix}Candidates"] = [
                    {
                        "machine_type": candidate.machine_type,
                        "cpu_milli": candidate.cpu_milli,
                        "memory_mib": candidate.memory_mib,
                        "task_count_per_node": candidate.task_count_per_node,
                    }
                    for candidate in candidates
                ]
                arguments[f"{prefix}Pinned"] = spec.stage_pinned.get(stage, False)

        if spec.forecast_repo_ref:
            arguments["forecastRepoRef"] = spec.forecast_repo_ref
        if spec.skip_output:
            arguments["runOutputStage"] = False
        if spec.output_config:
            arguments["outputConfigFile"] = spec.output_config

        return self._plan_pipeline_arguments(arguments)

    def _plan_pipeline_arguments(self, arguments: dict[str, Any]) -> SubmissionPlan:
        url = (
            "https://workflowexecutions.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.region}/"
            f"workflows/{self.workflow_name}/executions"
        )
        return SubmissionPlan(
            provider=self.provider,
            operation="pipeline",
            target=url,
            payload={"argument": json.dumps(arguments)},
            display_details={
                "url": url,
                "arguments": json.dumps(arguments, indent=2),
            },
            metadata={"arguments": arguments},
        )

    def submit_pipeline(self, plan: SubmissionPlan) -> RunRef:
        """Submit a previously prepared Workflows execution plan."""

        if plan.provider != self.provider or plan.operation != "pipeline":
            raise ValueError("GCP pipeline submission requires a GCP pipeline plan")

        token = self._get_token()
        response = self._http_post(
            plan.target,
            json=plan.payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        result = response.json()
        resource_name = result.get("name", "")
        return RunRef(
            provider=self.provider,
            kind="pipeline",
            run_id=resource_name.split("/")[-1] if resource_name else "",
            resource_name=resource_name,
        )

    def plan_job(self, spec: StageJobSpec) -> SubmissionPlan:
        """Build the exact legacy Cloud Batch job document without submitting it."""

        job_config = build_batch_job_config(
            stage=spec.stage,
            exp_id=spec.experiment_id,
            run_id=spec.run_id,
            task_index=spec.task_index,
            num_tasks=spec.num_tasks,
            output_config=spec.output_config,
            image_uri=spec.image_uri,
            bucket_name=spec.storage_bucket,
            dir_prefix=spec.storage_prefix,
            github_forecast_repo=spec.forecast_repo,
            project_id=self.project_id,
            cpu_milli=spec.resources.cpu_milli,
            memory_mib=spec.resources.memory_mib,
            machine_type=spec.resources.machine_type,
            max_run_duration=spec.resources.max_run_duration,
            task_count_per_node=spec.task_count_per_node,
            batch_sa_email=spec.execution_identity,
            profile=spec.profile,
            billing_project=spec.billing_project,
            skip_existing=spec.skip_existing,
        )
        target = f"projects/{self.project_id}/locations/{self.region}/jobs/{spec.job_id}"
        return SubmissionPlan(
            provider=self.provider,
            operation="job",
            target=target,
            payload=job_config,
            display_details={"job_config": json.dumps(job_config, indent=2)},
            metadata={"job_id": spec.job_id},
        )

    def submit_job(self, plan: SubmissionPlan) -> RunRef:
        """Submit a Cloud Batch job with the legacy gcloud command."""

        if plan.provider != self.provider or plan.operation != "job":
            raise ValueError("GCP job submission requires a GCP job plan")

        job_id = str(plan.metadata["job_id"])
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
            json.dump(plan.payload, handle, indent=2)
            temp_file = handle.name

        try:
            cmd = [
                "gcloud",
                "batch",
                "jobs",
                "submit",
                job_id,
                f"--project={self.project_id}",
                f"--location={self.region}",
                f"--config={temp_file}",
            ]
            result = self._command_runner(cmd, check=False)
            if result.returncode != 0:
                raise ExecutionBackendError(
                    "Job submission failed",
                    provider=self.provider,
                    operation="submit_job",
                    returncode=result.returncode,
                )
        finally:
            with contextlib.suppress(OSError):
                os.unlink(temp_file)

        return RunRef(
            provider=self.provider,
            kind="job",
            run_id=job_id,
            resource_name=plan.target,
        )

    def list_runs(self, query: RunQuery) -> list[RunRecord]:
        """List and enrich GCP Workflows executions."""

        token = self._get_token()
        executions = self._workflow_api.list_executions(
            self.project_id,
            self.region,
            self.workflow_name,
            token,
            query.limit,
            query.status,
        )
        if query.since:
            executions = [
                execution
                for execution in executions
                if self._parse_timestamp(execution.get("startTime", "")) > query.since
            ]
        if executions:
            executions = self._workflow_api.enrich_executions_with_arguments(
                executions, token, self.verbose
            )
        if query.experiment_id:
            executions = [
                execution
                for execution in executions
                if query.experiment_id
                in execution.get("argument", execution.get("workflowRevisionId", ""))
            ]
        return [self._record_from_execution(execution) for execution in executions]

    def resolve_run_ref(self, execution_id: str) -> RunRef:
        """Resolve a short or fully-qualified workflow execution ID."""

        resource_name = self._workflow_api.parse_execution_name(
            execution_id,
            self.project_id,
            self.region,
            self.workflow_name,
        )
        return RunRef(
            provider=self.provider,
            kind="pipeline",
            run_id=resource_name.split("/")[-1],
            resource_name=resource_name,
        )

    def describe_run(self, execution_id: str) -> RunRecord:
        """Fetch one GCP Workflows execution."""

        ref = self.resolve_run_ref(execution_id)
        token = self._get_token()
        execution = self._workflow_api.get_execution(ref.resource_name, token)
        return self._record_from_execution(execution, fallback_ref=ref)

    def cancel_run(self, execution_id: str, include_jobs: bool = True) -> CancelResult:
        """Cancel a workflow execution and discover its child Batch jobs."""

        ref = self.resolve_run_ref(execution_id)
        token = self._get_token()
        self._workflow_api.cancel_execution(ref.resource_name, token)

        children: list[ChildCancellation] = []
        if include_jobs:
            prefix = ref.run_id[:8]
            job_names: set[str] = set()
            for batch_region in self.batch_regions:
                discovered = self._workflow_api.list_batch_jobs_for_execution(
                    self.project_id,
                    batch_region,
                    ref.run_id,
                )
                job_names.update(
                    str(job["name"])
                    for job in discovered
                    if isinstance(job, dict) and job.get("name")
                )

            if not job_names:
                # Jobs created before execution_id labels used unsuffixed names.
                for batch_region in self.batch_regions:
                    for stage in ("a", "b", "c"):
                        legacy_id = f"stage-{stage}-{prefix}"
                        job_names.add(
                            f"projects/{self.project_id}/locations/{batch_region}/jobs/{legacy_id}"
                        )

            for job_name in sorted(job_names):
                job_id = job_name.rsplit("/", 1)[-1]
                try:
                    self._workflow_api.cancel_batch_job(job_name, token)
                    children.append(ChildCancellation(job_id, "cancelled"))
                except requests.HTTPError as exc:
                    response = exc.response
                    status_code = response.status_code if response is not None else None
                    if status_code == 404:
                        outcome = "not_found"
                    elif status_code == 400:
                        outcome = "already_complete"
                    else:
                        outcome = "failed"
                    children.append(
                        ChildCancellation(
                            job_id,
                            outcome,
                            status_code=status_code,
                            message=str(exc),
                        )
                    )
                except Exception as exc:
                    children.append(ChildCancellation(job_id, "failed", message=str(exc)))

        return CancelResult(ref, tuple(children))

    def plan_retry(self, execution_id: str) -> SubmissionPlan:
        """Read an execution and prepare a new submission with identical arguments."""

        record = self.describe_run(execution_id)
        argument = record.raw.get("argument", "{}")
        try:
            arguments = json.loads(argument)
        except json.JSONDecodeError:
            arguments = {}
        return self._plan_pipeline_arguments(arguments)

    def _record_from_execution(
        self,
        execution: dict[str, Any],
        fallback_ref: RunRef | None = None,
    ) -> RunRecord:
        resource_name = execution.get("name", "")
        ref = fallback_ref or RunRef(
            provider=self.provider,
            kind="pipeline",
            run_id=resource_name.split("/")[-1] if resource_name else "",
            resource_name=resource_name,
        )
        state = {
            "ACTIVE": RunState.RUNNING,
            "QUEUED": RunState.QUEUED,
            "SUCCEEDED": RunState.SUCCEEDED,
            "FAILED": RunState.FAILED,
            "CANCELLED": RunState.CANCELLED,
        }.get(execution.get("state", ""), RunState.UNKNOWN)
        return RunRecord(ref=ref, state=state, raw=execution)

    def _get_token(self) -> str:
        if self._token is None:
            try:
                self._token = self._token_provider()
            except Exception as exc:
                raise ExecutionAuthenticationError(str(exc), self.provider) from exc
        return self._token

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime:
        try:
            if timestamp.endswith("Z"):
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return datetime.fromisoformat(timestamp)
        except (ValueError, AttributeError):
            return datetime.min.replace(tzinfo=UTC)
