"""Contract and characterization tests for cloud execution backends."""

import json
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from epycloud.exceptions import ConfigError
from epycloud.execution import (
    PipelineRunSpec,
    RunQuery,
    RunState,
    StageJobSpec,
    StageResources,
    get_execution_backend,
)
from epycloud.execution.gcp import GcpExecutionBackend


def pipeline_spec() -> PipelineRunSpec:
    """Return a deterministic pipeline specification covering all optional fields."""

    return PipelineRunSpec(
        experiment_id="flu/weekly",
        run_id="20260818-120000-abc12345",
        storage_bucket="modeling-bucket",
        storage_prefix="pipeline/prod/flu/",
        forecast_repo="mobs-lab/forecast",
        forecast_repo_ref="release-2026",
        image_tag="sha-123",
        execution_identity="batch@test-project.iam.gserviceaccount.com",
        max_parallelism=75,
        task_count_per_node=2,
        stage_resources={
            "a": StageResources("c4d-standard-2", 2000, 8192, 3600),
            "b": StageResources("", 4000, 16384, 36000),
            "c": StageResources("c4d-standard-4", 4000, 15360, 7200),
        },
        profile="Flu Weekly",
        billing_project="Forecast Contract",
        skip_output=True,
        output_config="output_projection.yaml",
    )


def job_spec() -> StageJobSpec:
    """Return a deterministic stage job specification."""

    return StageJobSpec(
        job_id="stage-a-manual-deadbeef",
        stage="A",
        experiment_id="flu/weekly",
        run_id="20260818-120000-abc12345",
        task_index=0,
        num_tasks=None,
        output_config=None,
        image_uri="us-east5-docker.pkg.dev/test-project/repo/image:sha-123",
        storage_bucket="modeling-bucket",
        storage_prefix="pipeline/prod/flu/",
        forecast_repo="mobs-lab/forecast",
        resources=StageResources("c4d-standard-2", 2000, 8192, 3600),
        task_count_per_node=1,
        execution_identity="batch@test-project.iam.gserviceaccount.com",
        profile="Flu Weekly",
        billing_project="Forecast Contract",
    )


def test_factory_defaults_to_gcp(mock_config):
    backend = get_execution_backend(mock_config)

    assert isinstance(backend, GcpExecutionBackend)
    assert backend.provider == "gcp"


def test_factory_accepts_explicit_gcp(mock_config):
    mock_config["execution"] = {"provider": "GCP"}

    assert get_execution_backend(mock_config).provider == "gcp"


@pytest.mark.parametrize(
    ("execution", "message"),
    [
        (None, "execution must be a mapping"),
        ([], "execution must be a mapping"),
        ({"provider": None}, "execution.provider must be a non-empty string"),
        ({"provider": "  "}, "execution.provider must be a non-empty string"),
    ],
)
def test_factory_handles_legacy_and_rejects_malformed_execution_config(
    mock_config, execution, message
):
    mock_config["execution"] = execution

    with pytest.raises(ConfigError, match=message):
        get_execution_backend(mock_config)


def test_factory_rejects_unsupported_provider(mock_config):
    mock_config["execution"] = {"provider": "aws"}

    with pytest.raises(ConfigError, match="Unsupported execution provider: aws"):
        get_execution_backend(mock_config)


def test_gcp_pipeline_plan_matches_legacy_request(mock_config):
    token_provider = Mock(side_effect=AssertionError("planning must not authenticate"))
    http_post = Mock(side_effect=AssertionError("planning must not submit"))
    backend = GcpExecutionBackend(
        mock_config,
        token_provider=token_provider,
        http_post=http_post,
    )

    plan = backend.plan_pipeline(pipeline_spec())
    arguments = json.loads(plan.payload["argument"])

    assert plan.target == (
        "https://workflowexecutions.googleapis.com/v1/projects/test-project/"
        "locations/us-central1/workflows/epymodelingsuite-pipeline/executions"
    )
    assert arguments == {
        "bucket": "modeling-bucket",
        "dirPrefix": "pipeline/prod/flu/",
        "exp_id": "flu/weekly",
        "githubForecastRepo": "mobs-lab/forecast",
        "batchSaEmail": "batch@test-project.iam.gserviceaccount.com",
        "imageTag": "sha-123",
        "profile": "flu-weekly",
        "billingProject": "forecast-contract",
        "runId": "20260818-120000-abc12345",
        "maxParallelism": 75,
        "taskCountPerNode": 2,
        "stageAMachineType": "c4d-standard-2",
        "stageACpuMilli": 2000,
        "stageAMemoryMib": 8192,
        "stageCMachineType": "c4d-standard-4",
        "stageCCpuMilli": 4000,
        "stageCMemoryMib": 15360,
        "forecastRepoRef": "release-2026",
        "runOutputStage": False,
        "outputConfigFile": "output_projection.yaml",
    }
    token_provider.assert_not_called()
    http_post.assert_not_called()


def test_gcp_pipeline_submit_uses_planned_request(mock_config):
    response = Mock()
    response.json.return_value = {
        "name": "projects/test-project/locations/us-central1/workflows/"
        "epymodelingsuite-pipeline/executions/exec-123"
    }
    token_provider = Mock(return_value="test-token")
    http_post = Mock(return_value=response)
    backend = GcpExecutionBackend(
        mock_config,
        token_provider=token_provider,
        http_post=http_post,
    )
    plan = backend.plan_pipeline(pipeline_spec())

    ref = backend.submit_pipeline(plan)

    assert ref.run_id == "exec-123"
    assert ref.resource_name.endswith("/executions/exec-123")
    http_post.assert_called_once_with(
        plan.target,
        json=plan.payload,
        headers={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status.assert_called_once_with()


def test_gcp_job_plan_matches_legacy_batch_document(mock_config):
    backend = GcpExecutionBackend(mock_config)

    plan = backend.plan_job(job_spec())

    assert plan.target == (
        "projects/test-project/locations/us-central1/jobs/stage-a-manual-deadbeef"
    )
    assert plan.payload == {
        "labels": {
            "component": "epymodelingsuite",
            "stage": "builder",
            "exp_id": "flu-weekly",
            "run_id": "20260818-120000-abc12345",
            "managed-by": "manual",
            "profile": "flu-weekly",
            "billing_project": "forecast-contract",
        },
        "taskGroups": [
            {
                "taskCount": 1,
                "taskSpec": {
                    "runnables": [
                        {
                            "container": {
                                "imageUri": (
                                    "us-east5-docker.pkg.dev/test-project/repo/image:sha-123"
                                ),
                                "entrypoint": "/bin/bash",
                                "commands": ["/scripts/run_builder.sh"],
                            }
                        }
                    ],
                    "environment": {
                        "variables": {
                            "EXECUTION_MODE": "cloud",
                            "GCS_BUCKET": "modeling-bucket",
                            "DIR_PREFIX": "pipeline/prod/flu/",
                            "EXP_ID": "flu/weekly",
                            "RUN_ID": "20260818-120000-abc12345",
                            "GITHUB_FORECAST_REPO": "mobs-lab/forecast",
                        }
                    },
                    "computeResource": {"cpuMilli": 2000, "memoryMib": 8192},
                    "maxRunDuration": "3600s",
                },
                "taskCountPerNode": 1,
            }
        ],
        "logsPolicy": {"destination": "CLOUD_LOGGING"},
        "allocationPolicy": {
            "serviceAccount": {
                "email": "batch@test-project.iam.gserviceaccount.com"
            },
            "instances": [
                {
                    "policy": {
                        "machineType": "c4d-standard-2",
                        "provisioningModel": "STANDARD",
                        "bootDisk": {"type": "hyperdisk-balanced", "sizeGb": 50},
                    },
                    "installGpuDrivers": False,
                }
            ],
            "labels": {
                "profile": "flu-weekly",
                "billing_project": "forecast-contract",
            },
        },
    }


def test_gcp_job_plan_forwards_skip_existing_flag(mock_config):
    """The provider-neutral job flag reaches the Stage B container environment."""
    backend = GcpExecutionBackend(mock_config)
    spec = replace(job_spec(), stage="B", skip_existing=True)

    plan = backend.plan_job(spec)

    variables = plan.payload["taskGroups"][0]["taskSpec"]["environment"]["variables"]
    assert variables["SKIP_EXISTING"] == "true"


def test_gcp_job_submit_uses_exact_gcloud_argv_and_removes_temp_file(mock_config):
    observed: dict[str, object] = {}

    def command_runner(cmd, check):
        config_arg = next(value for value in cmd if value.startswith("--config="))
        config_path = config_arg.removeprefix("--config=")
        with open(config_path) as handle:
            observed["payload"] = json.load(handle)
        observed["cmd"] = cmd
        observed["config_path"] = config_path
        return subprocess.CompletedProcess(cmd, 0)

    backend = GcpExecutionBackend(mock_config, command_runner=command_runner)
    plan = backend.plan_job(job_spec())

    ref = backend.submit_job(plan)

    cmd = observed["cmd"]
    assert cmd[:5] == ["gcloud", "batch", "jobs", "submit", "stage-a-manual-deadbeef"]
    assert cmd[5:7] == ["--project=test-project", "--location=us-central1"]
    assert cmd[7].startswith("--config=")
    assert observed["payload"] == plan.payload
    assert not Path(observed["config_path"]).exists()
    assert ref.resource_name == plan.target


def test_gcp_list_contract_applies_filters_before_and_after_enrichment(mock_config):
    workflow_api = Mock()
    workflow_api.list_executions.return_value = [
        {
            "name": "projects/test/locations/us-central1/workflows/p/executions/old",
            "state": "SUCCEEDED",
            "startTime": "2026-08-17T00:00:00Z",
        },
        {
            "name": "projects/test/locations/us-central1/workflows/p/executions/current",
            "state": "ACTIVE",
            "startTime": "2026-08-18T12:00:00Z",
        },
    ]
    workflow_api.enrich_executions_with_arguments.side_effect = lambda rows, *_: [
        {**row, "argument": json.dumps({"exp_id": "target-exp"})} for row in rows
    ]
    backend = GcpExecutionBackend(
        mock_config,
        token_provider=Mock(return_value="token"),
        workflow_api=workflow_api,
    )

    records = backend.list_runs(
        RunQuery(
            limit=20,
            status="ACTIVE",
            since=datetime(2026, 8, 18, tzinfo=UTC),
            experiment_id="target-exp",
        )
    )

    assert [record.ref.run_id for record in records] == ["current"]
    assert records[0].state == RunState.RUNNING
    assert len(workflow_api.enrich_executions_with_arguments.call_args.args[0]) == 1
