"""Tests for the configurable Cloud Workflows workflow name (blue/green dev pipeline)."""

from unittest.mock import Mock, patch

import pytest

from epycloud.commands.status import operations as status_operations
from epycloud.execution import PipelineRunSpec, StageResources
from epycloud.execution.gcp import GcpExecutionBackend
from epycloud.lib.command_helpers import DEFAULT_WORKFLOW_NAME, get_workflow_name


def _pipeline_spec() -> PipelineRunSpec:
    """Minimal specification: only the submission target matters here."""

    return PipelineRunSpec(
        experiment_id="smoke-test",
        run_id=None,
        storage_bucket="modeling-bucket",
        storage_prefix="pipeline/dev/flu/",
        forecast_repo="mobs-lab/forecast",
        forecast_repo_ref="",
        image_tag="dev-test",
        execution_identity="batch@test-project.iam.gserviceaccount.com",
        max_parallelism=None,
        task_count_per_node=None,
        stage_resources={
            "a": StageResources("c4d-standard-2", 2000, 7168, 3600),
            "b": StageResources("", 2000, 7168, 36000),
            "c": StageResources("c4d-standard-4", 4000, 15360, 7200),
        },
    )


class TestGetWorkflowName:
    """The resolver must never change behaviour for configs that omit the key."""

    @pytest.mark.parametrize(
        "config",
        [
            {},
            {"google_cloud": {}},
            {"google_cloud": None},
            {"google_cloud": {"workflow_name": ""}},
            {"google_cloud": {"workflow_name": None}},
        ],
    )
    def test_falls_back_to_default(self, config):
        assert get_workflow_name(config) == "epymodelingsuite-pipeline"
        assert get_workflow_name(config) == DEFAULT_WORKFLOW_NAME

    def test_uses_configured_name(self):
        config = {"google_cloud": {"workflow_name": "epymodelingsuite-pipeline-dev"}}

        assert get_workflow_name(config) == "epymodelingsuite-pipeline-dev"


class TestBackendWorkflowName:
    """The GCP backend addresses whichever workflow config names."""

    def test_defaults_when_unset(self, mock_config):
        backend = GcpExecutionBackend(mock_config)

        assert backend.workflow_name == DEFAULT_WORKFLOW_NAME

    def test_targets_configured_workflow(self, mock_config):
        mock_config["google_cloud"]["workflow_name"] = "epymodelingsuite-pipeline-dev"

        backend = GcpExecutionBackend(mock_config)

        assert backend.workflow_name == "epymodelingsuite-pipeline-dev"

    def test_submission_target_follows_configured_workflow(self, mock_config):
        mock_config["google_cloud"]["workflow_name"] = "epymodelingsuite-pipeline-dev"
        backend = GcpExecutionBackend(mock_config)

        plan = backend.plan_pipeline(_pipeline_spec())

        assert plan.target == (
            "https://workflowexecutions.googleapis.com/v1/projects/test-project/"
            "locations/us-central1/workflows/epymodelingsuite-pipeline-dev/executions"
        )


class TestStatusQueriesWorkflowName:
    """`epycloud status` must query the same workflow the run was submitted to."""

    def _response(self):
        response = Mock()
        response.json.return_value = {"executions": []}
        response.raise_for_status.return_value = None
        return response

    def test_active_defaults_to_production_workflow(self):
        with patch.object(status_operations.requests, "get", return_value=self._response()) as get:
            with patch.object(status_operations, "get_gcloud_access_token", return_value="t"):
                status_operations.fetch_active_workflows("p", "us-central1", None, False)

        assert f"/workflows/{DEFAULT_WORKFLOW_NAME}/executions" in get.call_args[0][0]

    def test_active_uses_supplied_workflow(self):
        with patch.object(status_operations.requests, "get", return_value=self._response()) as get:
            with patch.object(status_operations, "get_gcloud_access_token", return_value="t"):
                status_operations.fetch_active_workflows(
                    "p", "us-central1", None, False, workflow_name="epymodelingsuite-pipeline-dev"
                )

        assert "/workflows/epymodelingsuite-pipeline-dev/executions" in get.call_args[0][0]
